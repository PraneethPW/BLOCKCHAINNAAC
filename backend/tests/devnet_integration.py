import os, sys, tempfile, uuid, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from eth_account import Account
from web3 import Web3
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
scratch=tempfile.TemporaryDirectory()
os.environ.update(DATABASE_URL='sqlite:///'+str(Path(scratch.name)/'test.db'),APP_ENV='development',AUTO_ANCHOR='false',LEDGER_NETWORK='private-devnet',LEDGER_RPC_URL='http://127.0.0.1:8545',LEDGER_PRIVATE_KEY=Account.create().key.hex())
from main import Base, engine, SessionLocal, Anchor, NetworkConfig
from anchor_worker import process, opaque
Base.metadata.create_all(engine)
case=str(uuid.uuid4());first=str(uuid.uuid4());appeal=str(uuid.uuid4())
stamp=datetime.now(timezone.utc)
with SessionLocal() as s:
    s.add(Anchor(id=first,case_id=case,document_hash=hashlib.sha256(b'Fictional QA document').hexdigest(),evidence_hash=hashlib.sha256(b'Fictional QA evidence').hexdigest(),outcome='confirmed_fraud',timestamp=stamp.isoformat()))
    s.add(Anchor(id=appeal,case_id=case,document_hash=hashlib.sha256(b'Fictional QA document').hexdigest(),evidence_hash=hashlib.sha256(b'Fictional QA appeal').hexdigest(),outcome='appeal_upheld',parent_id=first,timestamp=(stamp+timedelta(seconds=1)).isoformat()))
    s.commit()
process()
w3=Web3(Web3.HTTPProvider(os.environ['LEDGER_RPC_URL']))
with SessionLocal() as s:
    config=s.get(NetworkConfig,'private-devnet');assert w3.eth.get_code(config.address)
    txs=[s.get(Anchor,id).tx_hash for id in [first,appeal]]
    for id in [first,appeal]:
        a=s.get(Anchor,id);assert a.state=='Anchored on private Ethereum devnet';assert w3.eth.get_transaction_receipt(a.tx_hash).status==1
    a=s.get(Anchor,first);a.state='Queued';a.tx_hash='';s.commit()
process()
with SessionLocal() as s:assert [s.get(Anchor,id).tx_hash for id in [first,appeal]]==txs
os.environ['LEDGER_NETWORK']='sepolia';os.environ['SEPOLIA_RPC_URL']=os.environ['LEDGER_RPC_URL'];os.environ['LEDGER_CONTRACT_ADDRESS']=config.address
try:process();raise AssertionError('Wrong chain accepted')
except RuntimeError:pass
engine.dispose();scratch.cleanup()
print('Private-chain integration passed: deployment, confirmed receipt, linked appeal receipt, crash recovery, duplicate prevention and wrong-chain rejection.')
