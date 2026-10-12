"""Deploy the separate Sepolia vault, preserving a signed transaction before broadcast."""
import argparse,json,os
from pathlib import Path
from web3 import Web3
from web3.exceptions import TransactionNotFound

def deploy(journal_path):
    w3=Web3(Web3.HTTPProvider(os.environ['VAULT_SEPOLIA_RPC_URL'],request_kwargs={'timeout':30}))
    if w3.eth.chain_id!=11155111:raise RuntimeError('Deployment requires Ethereum Sepolia (11155111).')
    account=w3.eth.account.from_key(os.environ['VAULT_PRIVATE_KEY'])
    artifact=json.loads(Path(__file__).with_name('vault_contract.json').read_text())
    path=Path(journal_path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_file():
        journal=json.loads(path.read_text())
        if journal['writer']!=account.address or journal['chain_id']!=11155111:raise RuntimeError('Deployment journal belongs to another writer or network.')
    else:
        factory=w3.eth.contract(abi=artifact['abi'],bytecode=artifact['bytecode'])
        tx=factory.constructor().build_transaction({'from':account.address,'chainId':11155111,'nonce':w3.eth.get_transaction_count(account.address,'pending')})
        required=tx['gas']*tx.get('maxFeePerGas',tx.get('gasPrice',0))
        if w3.eth.get_balance(account.address)<required:raise RuntimeError('Fund the Sepolia writer with test ETH before deployment: '+account.address)
        signed=account.sign_transaction(tx)
        journal=dict(chain_id=11155111,writer=account.address,transaction=Web3.to_hex(signed.hash),raw_transaction=Web3.to_hex(signed.raw_transaction))
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(journal));temporary.replace(path)
    try:w3.eth.get_transaction(journal['transaction'])
    except TransactionNotFound:w3.eth.send_raw_transaction(bytes.fromhex(journal['raw_transaction'].removeprefix('0x')))
    receipt=w3.eth.wait_for_transaction_receipt(journal['transaction'],timeout=50)
    if receipt.status!=1:raise RuntimeError('Vault deployment reverted; retain the journal for investigation.')
    contract=w3.eth.contract(address=receipt.contractAddress,abi=artifact['abi'])
    if not w3.eth.get_code(receipt.contractAddress) or contract.functions.writer().call()!=account.address:raise RuntimeError('Deployed vault writer does not match.')
    result=dict(chain_id=11155111,writer=account.address,contract_address=receipt.contractAddress,transaction=journal['transaction'],block=receipt.blockNumber)
    path.write_text(json.dumps({**journal,**result},indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--journal',default='/data/vault-deployment.json');args=parser.parse_args()
    print(json.dumps(deploy(args.journal),indent=2))
