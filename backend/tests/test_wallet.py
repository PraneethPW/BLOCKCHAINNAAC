import base64,hashlib,json
import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from cryptography.exceptions import InvalidTag
import main,wallet
from test_workflow import account,upload

def signed(client,owner,key,document_id=''):
    r=client.post('/wallet/challenge',headers=owner,json={'address':key.address,'document_id':document_id})
    assert r.status_code==201,r.text
    c=r.json();signature=Account.sign_message(encode_defunct(text=c['message']),key.key).signature.hex()
    return dict(challenge_id=c['challenge_id'],signature=signature)

def setup(client,monkeypatch):
    monkeypatch.setenv('PINATA_JWT','test-only-credential');monkeypatch.setenv('VAULT_ENCRYPTION_KEY',base64.urlsafe_b64encode(b'k'*32).decode())
    owner=account(client);key=Account.create();body=signed(client,owner,key)
    assert client.post('/wallet/connect',headers=owner,json=body).status_code==200
    return owner,key

def test_signature_ownership_replay_and_account_isolation(client,monkeypatch):
    owner=account(client);key=Account.create();wrong=Account.create()
    request=client.post('/wallet/challenge',headers=owner,json={'address':key.address}).json()
    body=dict(challenge_id=request['challenge_id'],signature=Account.sign_message(encode_defunct(text=request['message']),wrong.key).signature.hex())
    assert client.post('/wallet/connect',headers=owner,json=body).status_code==403
    body['signature']=Account.sign_message(encode_defunct(text=request['message']),key.key).signature.hex()
    assert client.post('/wallet/connect',headers=owner,json=body).status_code==200
    assert client.post('/wallet/connect',headers=owner,json=body).status_code==403
    other=account(client,'other@example.com')
    assert client.post('/wallet/connect',headers=other,json=body).status_code==403
    assert client.post('/wallet/challenge',headers=other,json={'address':key.address}).status_code==409
    assert client.get('/wallet',headers=other).json()['address'] is None

def test_expired_challenge_and_no_wallet_reassignment(client):
    owner=account(client);key=Account.create();body=signed(client,owner,key)
    with main.SessionLocal() as s:
        c=s.get(wallet.WalletChallenge,body['challenge_id']);c.expires='2000-01-01';s.commit()
    assert client.post('/wallet/connect',headers=owner,json=body).status_code==403
    fresh=signed(client,owner,key);assert client.post('/wallet/connect',headers=owner,json=fresh).status_code==200
    assert client.post('/wallet/challenge',headers=owner,json={'address':Account.create().address}).status_code==409

def test_save_requires_specific_consent_and_exact_original(client,monkeypatch):
    owner,key=setup(client,monkeypatch);doc=upload(client,owner)
    connect_body=signed(client,owner,key)
    assert client.post('/wallet/documents',headers=owner,json=connect_body).status_code==403
    body=signed(client,owner,key,doc['id'])
    assert client.post('/wallet/documents',headers=owner,json=body).status_code==202
    assert client.post('/wallet/documents',headers=owner,json=body).status_code==403
    assert client.post('/wallet/documents',headers=owner,json=signed(client,owner,key,doc['id'])).json()['already_saved']
    results=client.get('/wallet',headers=owner).json()['documents']
    assert len(results)==1 and results[0]['state']=='queued' and not results[0]['cid'] and not results[0]['tx_hash']
    assert 'signature' not in results[0] and 'consent' not in results[0]
    assert not client.get('/wallet/documents/'+doc['id']+'/proof',headers=owner).json()['matched']
    other=account(client,'other@example.com')
    assert client.get('/wallet',headers=other).json()['documents']==[]
    assert client.get('/wallet/documents/'+doc['id']+'/file',headers=other).status_code==409

def test_changed_original_cannot_be_queued(client,monkeypatch):
    owner,key=setup(client,monkeypatch);doc=upload(client,owner);body=signed(client,owner,key,doc['id'])
    with main.SessionLocal() as s:
        original=s.get(main.Document,doc['id']);(main.STORAGE/original.storage_name).write_bytes(b'changed')
    assert client.post('/wallet/documents',headers=owner,json=body).status_code==409

def test_encryption_tamper_and_ipfs_retrieval(client,monkeypatch):
    owner,key=setup(client,monkeypatch);data=b'A real bounded test of encrypted storage.';doc=upload(client,owner,data)
    client.post('/wallet/documents',headers=owner,json=signed(client,owner,key,doc['id']))
    with main.SessionLocal() as s:
        entry=s.get(wallet.WalletDocument,doc['id']);payload=wallet.encrypt(data,entry)
        assert data not in payload and wallet.decrypt(payload,entry)==data
        with pytest.raises(InvalidTag):wallet.decrypt(payload[:-1]+bytes([payload[-1]^1]),entry)
        entry.cid='bafy'+'a'*40;entry.ciphertext_sha256=hashlib.sha256(payload).hexdigest();s.commit()
    async def retrieve(cid):return payload
    monkeypatch.setattr(wallet,'retrieve',retrieve)
    r=client.get('/wallet/documents/'+doc['id']+'/file',headers=owner)
    assert r.status_code==200 and r.content==data
    async def altered(cid):return payload+b'changed'
    monkeypatch.setattr(wallet,'retrieve',altered)
    assert client.get('/wallet/documents/'+doc['id']+'/file',headers=owner).status_code==502

def test_unpadded_encryption_configuration(monkeypatch):
    monkeypatch.setenv('VAULT_ENCRYPTION_KEY',base64.urlsafe_b64encode(b'k'*32).decode().rstrip('='))
    first=wallet.file_key('document-a')
    assert len(first)==32 and first!=wallet.file_key('document-b')
    monkeypatch.setenv('VAULT_ENCRYPTION_KEY','invalid')
    with pytest.raises(RuntimeError):wallet.file_key('document-a')

def test_worker_rejects_changed_encrypted_staging_before_upload(client,monkeypatch):
    import wallet_worker
    owner,key=setup(client,monkeypatch);doc=upload(client,owner)
    client.post('/wallet/documents',headers=owner,json=signed(client,owner,key,doc['id']))
    (main.STORAGE/(doc['id']+'.vault')).write_bytes(b'changed ciphertext')
    def no_network(*args,**kwargs):raise AssertionError('Changed staging must never be uploaded.')
    monkeypatch.setattr(wallet_worker.httpx,'Client',no_network)
    wallet_worker.process()
    with main.SessionLocal() as s:
        entry=s.get(wallet.WalletDocument,doc['id'])
        assert entry.state=='failed' and not entry.cid and not entry.tx_hash
        assert 'integrity validation' in entry.error
