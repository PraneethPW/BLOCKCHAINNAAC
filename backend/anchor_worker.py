"""Run a single worker. Persists transaction hashes before awaiting receipts.
Only Sepolia and explicitly selected private development chain 1337 are permitted.
"""
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from web3 import Web3
from web3.exceptions import TransactionNotFound
from sqlalchemy import select, text
from main import SessionLocal, Anchor, NetworkConfig, engine

def opaque(value):return hashlib.sha256(value.encode()).digest() if value else b'\0'*32
def process():
    network=os.getenv('LEDGER_NETWORK','sepolia')
    if network not in ['sepolia','private-devnet']:raise RuntimeError('Unsupported network.')
    private=network=='private-devnet';chain_id=1337 if private else 11155111
    state='Anchored on private Ethereum devnet' if private else 'Anchored on Sepolia'
    rpc=os.getenv('LEDGER_RPC_URL','') if private else os.getenv('SEPOLIA_RPC_URL','')
    address=os.getenv('LEDGER_CONTRACT_ADDRESS','');key=os.getenv('LEDGER_PRIVATE_KEY','')
    if not rpc or not key or (not private and not address):raise RuntimeError('Configure network and writer first.')
    w3=Web3(Web3.HTTPProvider(rpc,request_kwargs={'timeout':25}))
    if w3.eth.chain_id!=chain_id:raise RuntimeError('Chain ID does not match selected prototype network.')
    account=w3.eth.account.from_key(key)
    with engine.connect() as lock:
        if engine.dialect.name=='postgresql' and not lock.scalar(text('SELECT pg_try_advisory_lock(82917624)')):raise RuntimeError('Another anchor worker is active.')
        try:
            with SessionLocal() as s:
                start_block=int(os.getenv('LEDGER_START_BLOCK','0'))
                if private:
                    config=s.get(NetworkConfig,network)
                    if config:address=config.address;start_block=config.start_block
                    else:
                        # Development-only test currency. The chain is private, without a public RPC.
                        funded=w3.provider.make_request('evm_setAccountBalance',[account.address,hex(100*10**18)])
                        if 'error' in funded:raise RuntimeError('Private development funding unavailable.')
                        artifact=json.loads(Path(__file__).with_name('ledger_contract.json').read_text())
                        factory=w3.eth.contract(abi=artifact['abi'],bytecode=artifact['bytecode'])
                        tx=factory.constructor().build_transaction({'from':account.address,'chainId':chain_id,'nonce':w3.eth.get_transaction_count(account.address,'pending')})
                        signed=w3.eth.account.sign_transaction(tx,key)
                        receipt=w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(signed.raw_transaction),timeout=45)
                        if receipt.status!=1:raise RuntimeError('Contract deployment failed.')
                        address=receipt.contractAddress;start_block=receipt.blockNumber
                        s.add(NetworkConfig(network=network,address=address,start_block=start_block));s.commit()
                if not w3.eth.get_code(Web3.to_checksum_address(address)):raise RuntimeError('Persisted ledger missing. Restore the chain volume before proceeding.')
                contract=w3.eth.contract(address=Web3.to_checksum_address(address),abi=json.loads(Path(__file__).with_name('ledger_abi.json').read_text()))
                if not contract.functions.writers(account.address).call():raise RuntimeError('Configured wallet is not an authorized writer.')
                anchors=list(s.scalars(select(Anchor).where(Anchor.state!=state).order_by(Anchor.timestamp)))
                for a in anchors:
                    if a.parent_id:
                        parent=s.get(Anchor,a.parent_id)
                        if not parent or parent.state!=state:continue
                    rid=opaque(a.id)
                    record=contract.functions.records(rid).call()
                    if record[4]!=0:
                        if bytes(record[0])!=opaque(a.case_id) or bytes(record[1])!=bytes.fromhex(a.document_hash) or bytes(record[2])!=bytes.fromhex(a.evidence_hash) or bytes(record[3])!=opaque(a.parent_id) or record[5]!=(1 if a.outcome=='confirmed_fraud' else 2):raise RuntimeError('On-chain record mismatch; stop for investigation.')
                        # Recover a broadcast that succeeded before its DB acknowledgement.
                        logs=contract.events.DecisionAnchored().get_logs(from_block=start_block,argument_filters={'recordId':rid})
                        if not logs:raise RuntimeError('Record exists but its transaction could not be recovered.')
                        a.tx_hash=Web3.to_hex(logs[0]['transactionHash']);a.state=state;a.raw_transaction='';s.commit();continue
                    if not a.tx_hash:
                        transaction=contract.functions.anchor(rid,opaque(a.case_id),bytes.fromhex(a.document_hash),bytes.fromhex(a.evidence_hash),opaque(a.parent_id),int(datetime.fromisoformat(a.timestamp).timestamp()),1 if a.outcome=='confirmed_fraud' else 2).build_transaction({'from':account.address,'chainId':chain_id,'nonce':w3.eth.get_transaction_count(account.address,'pending')})
                        signed=w3.eth.account.sign_transaction(transaction,key)
                        # Persist the deterministic hash first; after a crash, rebroadcast is safe.
                        a.tx_hash=Web3.to_hex(signed.hash);a.raw_transaction=Web3.to_hex(signed.raw_transaction);a.state='Broadcast prepared';s.commit()
                    try:w3.eth.get_transaction(a.tx_hash)
                    except TransactionNotFound:
                        if not a.raw_transaction:raise RuntimeError('Signed transaction missing; operator recovery required.')
                        w3.eth.send_raw_transaction(bytes.fromhex(a.raw_transaction.removeprefix('0x')))
                    try:receipt=w3.eth.wait_for_transaction_receipt(a.tx_hash,timeout=45)
                    except Exception:
                        a.state='Pending receipt · retry worker';s.commit();continue
                    if receipt.status!=1:
                        a.state='Transaction reverted · retry required';a.tx_hash='';a.raw_transaction='';s.commit();continue
                    a.state=state;a.raw_transaction='';s.commit()
        finally:
            if engine.dialect.name=='postgresql':lock.execute(text('SELECT pg_advisory_unlock(82917624)'))

if __name__=='__main__':
    try:process();print('Anchoring pass complete.')
    except Exception as exc:
        # Never print provider errors which might include a credential-bearing RPC URL.
        print('Anchoring stopped. Check network, writer authorization, configuration, and transaction status.',file=sys.stderr)
        sys.exit(1)
