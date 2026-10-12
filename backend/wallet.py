"""Signed wallet ownership and authenticated access to encrypted IPFS references."""
import base64,hashlib,hmac,json,os,re,secrets
from datetime import datetime,timedelta,timezone
from pathlib import Path
import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from eth_account import Account as EthereumAccount
from eth_account.messages import encode_defunct
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import Response
from pydantic import BaseModel,Field
from sqlalchemy import String,Text,Integer,select
from sqlalchemy.orm import Mapped,mapped_column,Session
from sqlalchemy.exc import IntegrityError
from web3 import Web3
from main import Base,Account,Document,NetworkConfig,STORAGE,current,db,now,uid,canonical,get_document,document_list_json

router=APIRouter()
MAGIC=b'VERIS-VAULT-1\0'

class WalletBinding(Base):
    __tablename__='veris_wallet_bindings'
    user_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    address:Mapped[str]=mapped_column(String(42))
    connected_at:Mapped[str]=mapped_column(String(40),default=now)

class WalletChallenge(Base):
    __tablename__='veris_wallet_challenges'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    user_id:Mapped[str]=mapped_column(String(36),index=True)
    address:Mapped[str]=mapped_column(String(42))
    document_id:Mapped[str]=mapped_column(String(36),default='')
    message:Mapped[str]=mapped_column(Text)
    expires:Mapped[str]=mapped_column(String(40))
    consumed:Mapped[int]=mapped_column(Integer,default=0)

class WalletDocument(Base):
    __tablename__='veris_wallet_documents'
    document_id:Mapped[str]=mapped_column(String(36),primary_key=True)
    user_id:Mapped[str]=mapped_column(String(36),index=True)
    address:Mapped[str]=mapped_column(String(42))
    sha256:Mapped[str]=mapped_column(String(64))
    consent:Mapped[str]=mapped_column(Text)
    signature:Mapped[str]=mapped_column(String(132))
    network:Mapped[str]=mapped_column(String(30))
    state:Mapped[str]=mapped_column(String(30),default='queued')
    cid:Mapped[str]=mapped_column(String(100),default='')
    ciphertext_sha256:Mapped[str]=mapped_column(String(64),default='')
    tx_hash:Mapped[str]=mapped_column(String(80),default='')
    raw_transaction:Mapped[str]=mapped_column(Text,default='')
    contract_address:Mapped[str]=mapped_column(String(42),default='')
    error:Mapped[str]=mapped_column(Text,default='')
    created_at:Mapped[str]=mapped_column(String(40),default=now)
    updated_at:Mapped[str]=mapped_column(String(40),default=now)

def config():
    network=os.getenv('VAULT_NETWORK','private-devnet')
    if network not in ('private-devnet','sepolia'):raise HTTPException(503,'Unsupported vault network configuration.')
    record_configured=bool(os.getenv('LEDGER_RPC_URL') and os.getenv('LEDGER_PRIVATE_KEY')) if network=='private-devnet' else bool(os.getenv('VAULT_SEPOLIA_RPC_URL') and os.getenv('VAULT_PRIVATE_KEY') and os.getenv('VAULT_CONTRACT_ADDRESS'))
    return dict(network=network,chain_id=1337 if network=='private-devnet' else 11155111,record_configured=record_configured,
                label='Private Ethereum development network' if network=='private-devnet' else 'Sepolia testnet',
                pinata_configured=bool(os.getenv('PINATA_JWT')),encryption_configured=bool(os.getenv('VAULT_ENCRYPTION_KEY')),
                storage='AES-256-GCM encrypted IPFS',key_custody='Encryption keys are managed by the Veris backend; your wallet private key stays in your wallet.')

def address(value):
    if not re.fullmatch(r'0x[0-9a-fA-F]{40}',value) or int(value[2:],16)==0:raise HTTPException(400,'Enter a valid Ethereum wallet address.')
    return Web3.to_checksum_address(value)

def file_key(document_id):
    try:
        encoded=os.environ['VAULT_ENCRYPTION_KEY']
        master=base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4))
    except Exception:raise RuntimeError('Vault encryption is not configured.') from None
    if len(master)!=32:raise RuntimeError('Vault encryption key must contain 32 bytes.')
    return hmac.new(master,('veris-wallet-file:'+document_id).encode(),hashlib.sha256).digest()

def aad(entry):return canonical([entry.document_id,entry.address,entry.sha256]).encode()
def encrypt(data,entry):
    nonce=secrets.token_bytes(12)
    return MAGIC+nonce+AESGCM(file_key(entry.document_id)).encrypt(nonce,data,aad(entry))
def decrypt(payload,entry):
    if not payload.startswith(MAGIC):raise ValueError('Invalid encrypted vault file.')
    data=AESGCM(file_key(entry.document_id)).decrypt(payload[len(MAGIC):len(MAGIC)+12],payload[len(MAGIC)+12:],aad(entry))
    if hashlib.sha256(data).hexdigest()!=entry.sha256:raise ValueError('Decrypted original fingerprint does not match.')
    return data

def binding(u,s):
    b=s.get(WalletBinding,u.id)
    if not b:raise HTTPException(409,'Connect and sign with your wallet first.')
    return b

def consume(body,u,s,purpose):
    challenge=s.scalar(select(WalletChallenge).where(WalletChallenge.id==body.challenge_id).with_for_update())
    if not challenge or challenge.user_id!=u.id or challenge.consumed or challenge.expires<now():raise HTTPException(403,'Wallet request is expired or already used. Request a new signature.')
    if bool(challenge.document_id)!=(purpose=='save'):raise HTTPException(403,'This signature is for a different action.')
    try:recovered=EthereumAccount.recover_message(encode_defunct(text=challenge.message),signature=body.signature)
    except Exception:raise HTTPException(403,'Wallet signature is invalid.') from None
    if recovered!=challenge.address:raise HTTPException(403,'The signature does not match the requested wallet.')
    challenge.consumed=1
    return challenge

class ChallengeInput(BaseModel):
    address:str=Field(max_length=42)
    document_id:str=Field(default='',max_length=36)
class SignedInput(BaseModel):
    challenge_id:str=Field(max_length=36)
    signature:str=Field(min_length=130,max_length=132)

@router.post('/wallet/challenge',status_code=201)
def challenge(body:ChallengeInput,request:Request,u:Account=Depends(current),s:Session=Depends(db)):
    wallet=address(body.address)
    existing=s.get(WalletBinding,u.id)
    if existing and existing.address!=wallet:raise HTTPException(409,'This Veris account already has a linked wallet. Select '+existing.address+' in your wallet app to continue.')
    domain=request.headers.get('origin') or os.getenv('FRONTEND_ORIGINS','http://localhost:5173').split(',')[0]
    nonce=secrets.token_hex(16);expires=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
    if body.document_id:
        b=binding(u,s)
        if b.address!=wallet:raise HTTPException(403,'Select your linked wallet.')
        doc=get_document(s,body.document_id,u)
        if doc.owner_id!=u.id:raise HTTPException(403,'Only the submitting account can save this document to its wallet.')
        file=STORAGE/doc.storage_name
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=doc.sha256:raise HTTPException(409,'Restore the unchanged original before saving to your wallet.')
        cfg=config()
        if not cfg['pinata_configured'] or not cfg['encryption_configured']:raise HTTPException(503,'Encrypted IPFS storage has not been configured by the operator.')
        action=f"Store document {doc.id}\nSHA-256: {doc.sha256}\nStorage: encrypted IPFS\nRecord network: {cfg['label']}\nI authorize Veris to register this reference for my wallet. This does not declare the file genuine."
    else:action='Connect this wallet to my signed-in Veris workspace. This link does not grant access to documents in other Veris accounts. No token allowance or transfer is requested.'
    message=f"Veris wallet authorization\nOrigin: {domain}\nWallet: {wallet}\nVeris account: {u.email}\nWorkspace: {u.id}\n{action}\nNonce: {nonce}\nExpires: {expires}"
    c=WalletChallenge(user_id=u.id,address=wallet,document_id=body.document_id,message=message,expires=expires);s.add(c);s.commit()
    return dict(challenge_id=c.id,message=message,expires=expires)

@router.post('/wallet/connect')
def connect(body:SignedInput,u:Account=Depends(current),s:Session=Depends(db)):
    c=consume(body,u,s,'connect')
    prior=s.get(WalletBinding,u.id)
    if prior and prior.address!=c.address:raise HTTPException(409,'This Veris account already has a different linked wallet. Select '+prior.address+' in your wallet app to continue.')
    if not prior:s.add(WalletBinding(user_id=u.id,address=c.address))
    try:s.commit()
    except IntegrityError:
        s.rollback();raise HTTPException(409,'This Veris account was linked by another request. Refresh the wallet page to see its saved connection.') from None
    return dict(address=c.address,connected=True)

@router.post('/wallet/documents',status_code=202)
def save(body:SignedInput,u:Account=Depends(current),s:Session=Depends(db)):
    b=binding(u,s);c=consume(body,u,s,'save');doc=get_document(s,c.document_id,u,True)
    if doc.owner_id!=u.id or c.address!=b.address:raise HTTPException(403,'The document or wallet does not belong to this workspace.')
    if f'SHA-256: {doc.sha256}' not in c.message or f"Record network: {config()['label']}" not in c.message:raise HTTPException(409,'Document identity or network changed. Sign a new save request.')
    prior=s.get(WalletDocument,doc.id)
    if prior:s.commit();return dict(document_id=doc.id,state=prior.state,already_saved=True)
    file=STORAGE/doc.storage_name
    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=doc.sha256:raise HTTPException(409,'The original changed after authorization.')
    entry=WalletDocument(document_id=doc.id,user_id=u.id,address=b.address,sha256=doc.sha256,consent=c.message,signature=body.signature,network=config()['network'])
    s.add(entry);s.commit();return dict(document_id=doc.id,state='queued',already_saved=False)

def owned(id,u,s):
    entry=s.get(WalletDocument,id);b=binding(u,s)
    if not entry or entry.user_id!=u.id or entry.address!=b.address:raise HTTPException(404,'Wallet document not found.')
    doc=get_document(s,id,u)
    return entry,doc

@router.get('/wallet')
def dashboard(u:Account=Depends(current),s:Session=Depends(db)):
    b=s.get(WalletBinding,u.id)
    entries=list(s.scalars(select(WalletDocument).where(WalletDocument.user_id==u.id).order_by(WalletDocument.created_at.desc())))
    ids=[e.document_id for e in entries]
    docs=list(s.scalars(select(Document).where(Document.id.in_(ids)))) if ids else []
    from main import Archive
    archived=set(s.scalars(select(Archive.id).where(Archive.id.in_(ids)))) if ids else set()
    results={d['id']:d for d in document_list_json(docs,s)}
    fields=['document_id','address','sha256','network','state','cid','ciphertext_sha256','tx_hash','contract_address','error','created_at','updated_at']
    return dict(address=b.address if b else None,connected_at=b.connected_at if b else None,services=config(),documents=[dict(**{k:getattr(e,k) for k in fields},document=results[e.document_id]) for e in entries if e.document_id in results and e.document_id not in archived])

@router.post('/wallet/documents/{id}/retry')
def retry(id:str,u:Account=Depends(current),s:Session=Depends(db)):
    entry,doc=owned(id,u,s)
    if entry.state!='failed':raise HTTPException(409,'Only a failed save can be retried.')
    entry.state='pinned' if entry.cid else 'queued';entry.error='';entry.updated_at=now();s.commit();return dict(state=entry.state)

async def retrieve(cid):
    if not re.fullmatch(r'(?:b[a-z2-7]{20,99}|Qm[1-9A-HJ-NP-Za-km-z]{44})',cid):raise ValueError('Invalid IPFS reference.')
    async with httpx.AsyncClient(timeout=25,follow_redirects=False) as client:
        async with client.stream('GET','https://gateway.pinata.cloud/ipfs/'+cid) as response:
            response.raise_for_status();chunks=[];size=0
            async for chunk in response.aiter_bytes():
                size+=len(chunk)
                if size>11*1024*1024:raise ValueError('Vault file exceeds limit.')
                chunks.append(chunk)
            return b''.join(chunks)

@router.get('/wallet/documents/{id}/file')
async def download(id:str,u:Account=Depends(current),s:Session=Depends(db)):
    entry,doc=owned(id,u,s)
    if not entry.cid:raise HTTPException(409,'IPFS upload is not complete.')
    try:
        payload=await retrieve(entry.cid)
        if hashlib.sha256(payload).hexdigest()!=entry.ciphertext_sha256:raise ValueError('Encrypted fingerprint differs.')
        data=decrypt(payload,entry)
    except Exception:raise HTTPException(502,'IPFS retrieval or integrity verification failed. Retry without changing the stored evidence.') from None
    return Response(data,media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="document{Path(doc.filename).suffix}"'})

@router.get('/wallet/documents/{id}/proof')
def proof(id:str,u:Account=Depends(current),s:Session=Depends(db)):
    entry,doc=owned(id,u,s)
    from wallet_worker import check_proof
    return check_proof(entry,s)
