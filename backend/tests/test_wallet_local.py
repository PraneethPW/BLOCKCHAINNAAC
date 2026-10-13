import base64,hashlib,json,threading
from types import SimpleNamespace
import pytest,httpx
from fastapi.testclient import TestClient
from eth_account import Account
from web3.datastructures import AttributeDict
import main,wallet,wallet_worker
from wallet_runtime import ledger_enabled,wallet_enabled
from test_workflow import account,upload
from test_wallet import setup,signed

def test_wallet_worker_switch_is_independent_and_backward_compatible(monkeypatch):
    monkeypatch.setenv('AUTO_ANCHOR','false');monkeypatch.delenv('AUTO_WALLET_STORAGE',raising=False)
    assert not wallet_enabled() and not ledger_enabled()
    monkeypatch.setenv('AUTO_ANCHOR','true')
    assert wallet_enabled() and ledger_enabled()
    monkeypatch.setenv('AUTO_WALLET_STORAGE','false')
    assert not wallet_enabled() and ledger_enabled()
    monkeypatch.setenv('AUTO_ANCHOR','false');monkeypatch.setenv('AUTO_WALLET_STORAGE','true')
    assert wallet_enabled() and not ledger_enabled()

def test_lifespan_starts_wallet_without_starting_fraud_worker(monkeypatch):
    import anchor_worker
    ran_wallet=threading.Event();ran_ledger=threading.Event()
    monkeypatch.setenv('AUTO_ANCHOR','false');monkeypatch.setenv('AUTO_WALLET_STORAGE','true');monkeypatch.setenv('AUTO_VERIFY','false')
    monkeypatch.setattr(wallet_worker,'process',lambda:ran_wallet.set())
    monkeypatch.setattr(anchor_worker,'process',lambda:ran_ledger.set())
    with TestClient(main.app):
        assert ran_wallet.wait(3)
        assert not ran_ledger.is_set()

def test_wallet_reports_missing_settings_without_exposing_secrets(client,monkeypatch):
    owner=account(client);monkeypatch.setenv('VAULT_NETWORK','sepolia');monkeypatch.setenv('AUTO_ANCHOR','false')
    monkeypatch.delenv('AUTO_WALLET_STORAGE',raising=False)
    for name in ['PINATA_JWT','VAULT_ENCRYPTION_KEY','VAULT_PRIVATE_KEY','VAULT_CONTRACT_ADDRESS','VAULT_SEPOLIA_RPC_URL']:monkeypatch.delenv(name,raising=False)
    services=client.get('/wallet',headers=owner).json()['services']
    assert services['worker_enabled'] is False and services['save_ready'] is False
    assert 'VAULT_PRIVATE_KEY' in services['missing_settings']
    secret='local-only-test-secret'
    monkeypatch.setenv('PINATA_JWT',secret);monkeypatch.setenv('VAULT_ENCRYPTION_KEY',base64.urlsafe_b64encode(b'k'*32).decode())
    monkeypatch.setenv('VAULT_SEPOLIA_RPC_URL','https://example.com');monkeypatch.setenv('VAULT_PRIVATE_KEY','invalid-key');monkeypatch.setenv('VAULT_CONTRACT_ADDRESS','invalid-address')
    services=client.get('/wallet',headers=owner).json()['services']
    assert services['invalid_settings']==['VAULT_PRIVATE_KEY','VAULT_CONTRACT_ADDRESS']
    assert secret not in json.dumps(services) and 'invalid-key' not in json.dumps(services)
    monkeypatch.setenv('VAULT_PRIVATE_KEY',Account.create().key.hex());monkeypatch.setenv('VAULT_CONTRACT_ADDRESS','0x'+'1'*40);monkeypatch.setenv('AUTO_WALLET_STORAGE','true')
    assert client.get('/wallet',headers=owner).json()['services']['save_ready'] is True

def test_proof_read_only_still_binds_writer_and_original_fields(client,monkeypatch):
    owner,key=setup(client,monkeypatch);doc=upload(client,owner)
    client.post('/wallet/documents',headers=owner,json=signed(client,owner,key,doc['id']))
    relay=Account.create();contract_address='0x'+'1'*40
    monkeypatch.setenv('VAULT_CONTRACT_ADDRESS',contract_address);monkeypatch.setenv('VAULT_SEPOLIA_RPC_URL','https://example.com');monkeypatch.delenv('VAULT_PRIVATE_KEY',raising=False)
    with main.SessionLocal() as session:
        entry=session.get(wallet.WalletDocument,doc['id']);entry.network='sepolia';entry.cid='bafy'+'a'*40;entry.tx_hash='0x'+'2'*64;entry.contract_address=contract_address;session.commit()
        consent=hashlib.sha256(entry.consent.encode()).digest()
        row=[entry.address,bytes.fromhex(entry.sha256),entry.cid,consent,100]
        receipt={'status':1,'to':contract_address,'from':relay.address,'blockNumber':100,'blockHash':b'block'}
        call=lambda value:SimpleNamespace(call=lambda:value)
        events=[{'args':{'id':wallet_worker.opaque(entry.document_id),'owner':entry.address,'fileHash':bytes.fromhex(entry.sha256),'cid':entry.cid,'consentHash':consent}}]
        contract=SimpleNamespace(functions=SimpleNamespace(writer=lambda:call(relay.address),getDocument=lambda id:call(row)),events=SimpleNamespace(DocumentStored=lambda:SimpleNamespace(process_receipt=lambda r:events)))
        eth=SimpleNamespace(get_transaction_receipt=lambda tx:AttributeDict(receipt),get_block=lambda n:SimpleNamespace(hash=b'block'),contract=lambda **kw:contract,account=Account)
        monkeypatch.setattr(wallet_worker,'chain',lambda network:(SimpleNamespace(eth=eth),11155111))
        assert wallet_worker.check_proof(entry,session)['matched']
        receipt['from']=key.address
        assert wallet_worker.check_proof(entry,session)['state']=='mismatch'
        receipt['from']=relay.address;row[2]='different-cid'
        assert not wallet_worker.check_proof(entry,session)['matched']
        row[2]=entry.cid;monkeypatch.setenv('VAULT_PRIVATE_KEY',key.key.hex())
        assert wallet_worker.check_proof(entry,session)['state']=='mismatch'

def test_ipfs_download_distinguishes_wrong_key_and_provider_failure(client,monkeypatch):
    owner,key=setup(client,monkeypatch);data=b'Encrypted local retrieval regression.';doc=upload(client,owner,data)
    client.post('/wallet/documents',headers=owner,json=signed(client,owner,key,doc['id']))
    with main.SessionLocal() as session:
        entry=session.get(wallet.WalletDocument,doc['id']);payload=wallet.encrypt(data,entry)
        entry.cid='bafy'+'a'*40;entry.ciphertext_sha256=hashlib.sha256(payload).hexdigest();session.commit()
    async def retrieve(cid):return payload
    monkeypatch.setattr(wallet,'retrieve',retrieve)
    monkeypatch.setenv('VAULT_ENCRYPTION_KEY',base64.urlsafe_b64encode(b'x'*32).decode())
    response=client.get('/wallet/documents/'+doc['id']+'/file',headers=owner)
    assert response.status_code==502 and 'original VAULT_ENCRYPTION_KEY' in response.json()['detail']
    monkeypatch.delenv('VAULT_ENCRYPTION_KEY')
    assert client.get('/wallet/documents/'+doc['id']+'/file',headers=owner).status_code==503
    monkeypatch.setenv('VAULT_ENCRYPTION_KEY',base64.urlsafe_b64encode(b'k'*32).decode())
    async def timeout(cid):raise httpx.ReadTimeout('secret provider request details must not leak')
    monkeypatch.setattr(wallet,'retrieve',timeout)
    response=client.get('/wallet/documents/'+doc['id']+'/file',headers=owner)
    assert response.status_code==504 and 'secret provider' not in response.text

def test_diagnostic_has_no_secret_values(client,monkeypatch):
    from diagnose_wallet import diagnose
    monkeypatch.setenv('PINATA_JWT','private-test-credential')
    result=diagnose()
    assert result['database']['connected']
    assert 'private-test-credential' not in json.dumps(result)
