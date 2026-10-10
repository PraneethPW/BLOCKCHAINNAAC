"""Deploy the compiled contract using environment credentials; requires Sepolia test ETH."""
import json,os
from pathlib import Path
from web3 import Web3
w3=Web3(Web3.HTTPProvider(os.environ['SEPOLIA_RPC_URL']))
if w3.eth.chain_id!=11155111:raise SystemExit('Sepolia only.')
wallet=w3.eth.account.from_key(os.environ['LEDGER_PRIVATE_KEY'])
artifact_path=Path(os.getenv('LEDGER_ARTIFACT',str(Path(__file__).parent.parent/'contracts'/'VerisLedger.json')))
artifact=json.loads(artifact_path.read_text())
contract=w3.eth.contract(abi=artifact['abi'],bytecode=artifact['bytecode'])
tx=contract.constructor().build_transaction({'from':wallet.address,'chainId':11155111,'nonce':w3.eth.get_transaction_count(wallet.address,'pending')})
signed=w3.eth.account.sign_transaction(tx,os.environ['LEDGER_PRIVATE_KEY'])
tx_hash=w3.eth.send_raw_transaction(signed.raw_transaction)
receipt=w3.eth.wait_for_transaction_receipt(tx_hash,timeout=120)
if receipt.status!=1:raise SystemExit('Contract deployment reverted.')
print('LEDGER_CONTRACT_ADDRESS='+receipt.contractAddress)
print('LEDGER_START_BLOCK='+str(receipt.blockNumber))
