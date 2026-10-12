"""Pin encrypted originals and preserve actual, crash-recoverable vault transactions."""
import hashlib,json,os
from pathlib import Path
import httpx
from web3 import Web3
from web3.exceptions import TransactionNotFound
from sqlalchemy import select,text
from main import SessionLocal,engine,STORAGE,Document,NetworkConfig,now
from wallet import WalletDocument,encrypt,decrypt

def chain(network):
    if network not in ['private-devnet','sepolia']:raise RuntimeError('Unsupported vault network.')
    private=network=='private-devnet';expected=1337 if private else 11155111
    rpc=os.getenv('LEDGER_RPC_URL','') if private else os.getenv('VAULT_SEPOLIA_RPC_URL','')
    if not rpc:raise RuntimeError('Vault RPC is not configured.')
    w3=Web3(Web3.HTTPProvider(rpc,request_kwargs={'timeout':20}))
    if w3.eth.chain_id!=expected:raise RuntimeError('Vault chain ID differs from configured network.')
    return w3,expected

def artifact():return json.loads(Path(__file__).with_name('vault_contract.json').read_text())
def opaque(id):return hashlib.sha256(id.encode()).digest()

def check_proof(entry,s):
    result=dict(state='pending',matched=False,network=entry.network,transaction=entry.tx_hash,contract=entry.contract_address,cid=entry.cid,detail='A successful matching blockchain receipt is required.')
    if not entry.tx_hash or not entry.contract_address:return result
    try:
        w3,chain_id=chain(entry.network);receipt=w3.eth.get_transaction_receipt(entry.tx_hash)
        block=w3.eth.get_block(receipt.blockNumber)
        contract=w3.eth.contract(address=Web3.to_checksum_address(entry.contract_address),abi=artifact()['abi'])
        row=contract.functions.getDocument(opaque(entry.document_id)).call()
        events=contract.events.DocumentStored().process_receipt(receipt)
        consent=hashlib.sha256(entry.consent.encode()).digest()
        matches=receipt.status==1 and receipt.to.lower()==entry.contract_address.lower() and receipt.blockHash==block.hash and row[0]==entry.address and bytes(row[1]).hex()==entry.sha256 and row[2]==entry.cid and bytes(row[3])==consent
        matches=matches and any(bytes(e['args']['id'])==opaque(entry.document_id) and e['args']['owner']==entry.address and bytes(e['args']['fileHash']).hex()==entry.sha256 and e['args']['cid']==entry.cid and bytes(e['args']['consentHash'])==consent for e in events)
        result.update(state='matched' if matches else 'mismatch',matched=bool(matches),chain_id=chain_id,block=receipt.blockNumber,detail='Receipt, canonical block, owner, original fingerprint, encrypted CID and signed consent commitment match.' if matches else 'The transaction or contract fields do not match this wallet reference.')
    except TransactionNotFound:result['detail']='The transaction receipt is not available yet.'
    except Exception:result.update(state='unavailable',detail='The blockchain could not be checked. No positive match was inferred.')
    return result

def deploy(w3,key,account,chain_id,network,s):
    name='wallet-v1:'+network;config=s.get(NetworkConfig,name)
    if config:
        if not w3.eth.get_code(Web3.to_checksum_address(config.address)):raise RuntimeError('Persisted vault contract is missing. Restore the chain before retrying.')
        return config.address
    configured=os.getenv('VAULT_CONTRACT_ADDRESS','') if network=='sepolia' else ''
    if configured:
        address=Web3.to_checksum_address(configured)
        if not w3.eth.get_code(address):raise RuntimeError('Configured vault contract is missing.')
        s.add(NetworkConfig(network=name,address=address,start_block=0));s.commit();return address
    if network!='private-devnet':raise RuntimeError('Deploy and configure the Sepolia vault contract first.')
    funded=w3.provider.make_request('evm_setAccountBalance',[account.address,hex(100*10**18)])
    if 'error' in funded:raise RuntimeError('Private development funding unavailable.')
    a=artifact();factory=w3.eth.contract(abi=a['abi'],bytecode=a['bytecode'])
    tx=factory.constructor().build_transaction({'from':account.address,'chainId':chain_id,'nonce':w3.eth.get_transaction_count(account.address,'pending')})
    signed=w3.eth.account.sign_transaction(tx,key)
    receipt=w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(signed.raw_transaction),timeout=40)
    if receipt.status!=1:raise RuntimeError('Vault deployment reverted.')
    s.add(NetworkConfig(network=name,address=receipt.contractAddress,start_block=receipt.blockNumber));s.commit();return receipt.contractAddress

def process():
    # Sharing the fraud writer lock prevents nonce collisions between contracts.
    with engine.connect() as lock:
        if engine.dialect.name=='postgresql' and not lock.scalar(text('SELECT pg_try_advisory_lock(82917624)')):return
        try:
            with SessionLocal() as s:
                entry=s.scalar(select(WalletDocument).where(WalletDocument.state.in_(['queued','pinning','pinned','broadcast'])).order_by(WalletDocument.created_at).with_for_update())
                if not entry:return
                try:
                    doc=s.get(Document,entry.document_id)
                    if not doc:raise RuntimeError('The original document is missing.')
                    if not entry.cid:
                        data=(STORAGE/doc.storage_name).read_bytes()
                        if hashlib.sha256(data).hexdigest()!=entry.sha256:raise RuntimeError('Original fingerprint changed. Restore the submitted file.')
                        path=STORAGE/(entry.document_id+'.vault')
                        if not path.is_file():path.write_bytes(encrypt(data,entry))
                        payload=path.read_bytes()
                        try:decrypt(payload,entry)
                        except Exception:raise RuntimeError('Encrypted staging file failed integrity validation. Restore the intact vault staging file before retrying.') from None
                        entry.ciphertext_sha256=hashlib.sha256(payload).hexdigest();entry.state='pinning';entry.updated_at=now();s.commit()
                        token=os.getenv('PINATA_JWT','')
                        if not token:raise RuntimeError('Pinata authentication is not configured.')
                        with httpx.Client(timeout=45,follow_redirects=False) as client:
                            response=client.post('https://uploads.pinata.cloud/v3/files',headers={'Authorization':'Bearer '+token},data={'network':'public','name':entry.document_id+'.vault'},files={'file':(entry.document_id+'.vault',payload,'application/octet-stream')})
                        if response.status_code not in (200,201):raise RuntimeError('Encrypted IPFS upload was rejected. Check Pinata access and storage quota.')
                        cid=response.json().get('data',{}).get('cid','')
                        import re
                        if not re.fullmatch(r'(?:b[a-z2-7]{20,99}|Qm[1-9A-HJ-NP-Za-km-z]{44})',cid):raise RuntimeError('IPFS did not return a valid content reference.')
                        entry.cid=cid;entry.state='pinned';entry.updated_at=now();s.commit()
                    w3,chain_id=chain(entry.network)
                    key=os.getenv('LEDGER_PRIVATE_KEY','') if entry.network=='private-devnet' else os.getenv('VAULT_PRIVATE_KEY','')
                    if not key:raise RuntimeError('The vault transaction writer is not configured.')
                    account=w3.eth.account.from_key(key)
                    entry.contract_address=deploy(w3,key,account,chain_id,entry.network,s)
                    contract=w3.eth.contract(address=entry.contract_address,abi=artifact()['abi'])
                    if contract.functions.writer().call()!=account.address:raise RuntimeError('The configured vault writer is not authorized.')
                    if not entry.tx_hash:
                        tx=contract.functions.store(opaque(entry.document_id),entry.address,bytes.fromhex(entry.sha256),entry.cid,hashlib.sha256(entry.consent.encode()).digest()).build_transaction({'from':account.address,'chainId':chain_id,'nonce':w3.eth.get_transaction_count(account.address,'pending')})
                        signed=w3.eth.account.sign_transaction(tx,key);entry.tx_hash=Web3.to_hex(signed.hash);entry.raw_transaction=Web3.to_hex(signed.raw_transaction);entry.state='broadcast';entry.updated_at=now();s.commit()
                    try:w3.eth.get_transaction(entry.tx_hash)
                    except TransactionNotFound:w3.eth.send_raw_transaction(bytes.fromhex(entry.raw_transaction.removeprefix('0x')))
                    try:receipt=w3.eth.wait_for_transaction_receipt(entry.tx_hash,timeout=35)
                    except Exception:return  # Retain the signed transaction for a later pass.
                    if receipt.status!=1:raise RuntimeError('The vault transaction reverted. Operator investigation is required.')
                    if not check_proof(entry,s)['matched']:raise RuntimeError('The vault receipt did not match its stored reference.')
                    entry.state='anchored';entry.raw_transaction='';entry.error='';entry.updated_at=now();s.commit()
                except Exception as exc:
                    s.rollback();entry=s.get(WalletDocument,entry.document_id)
                    entry.state='failed';entry.error=str(exc) if isinstance(exc,RuntimeError) else 'Vault save failed. The original remains available; retry after checking storage and network access.'
                    entry.updated_at=now();s.commit()
        finally:
            if engine.dialect.name=='postgresql':lock.execute(text('SELECT pg_advisory_unlock(82917624)'))
