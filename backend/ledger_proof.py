"""Read-only Ethereum audit checks, also usable outside the application."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from web3 import Web3
from web3.exceptions import TransactionNotFound


def opaque(value):return '0x'+(hashlib.sha256(value.encode()).hexdigest() if value else '00'*32)


def expected_record(anchor):
    return dict(record_id=opaque(anchor.id),case_id=opaque(anchor.case_id),document_hash='0x'+anchor.document_hash,
                evidence_hash='0x'+anchor.evidence_hash,parent_record_id=opaque(anchor.parent_id),
                timestamp=int(datetime.fromisoformat(anchor.timestamp).timestamp()),outcome=1 if anchor.outcome=='confirmed_fraud' else 2)


def network_config(session):
    from main import NetworkConfig
    network=os.getenv('LEDGER_NETWORK','sepolia')
    config=session.get(NetworkConfig,network)
    address=config.address if config else os.getenv('LEDGER_CONTRACT_ADDRESS','')
    private=network=='private-devnet'
    rpc=os.getenv('LEDGER_RPC_URL','') if private else os.getenv('SEPOLIA_RPC_URL','')
    return network,address,1337 if private else 11155111,rpc


def payload_binding(bundle):
    """Bind expected fields to the exact snapshot, not editable bundle flags."""
    try:
        payload=bundle['canonical_payload'];manifest=json.loads(payload);expected=bundle['expected_record']
        digest=hashlib.sha256(payload.encode()).hexdigest()
        if digest!=bundle['snapshot_digest'] or '0x'+digest!=expected['evidence_hash']:return False
        if expected['record_id']!=opaque(bundle['record_id']) or expected['case_id']!=opaque(bundle['document_id']):return False
        if manifest.get('schema')=='veris-accreditation-evidence/1':
            decision=manifest['decision'];doc=manifest['document']
            return (decision['id']==bundle['record_id'] and doc['id']==bundle['document_id'] and
                    '0x'+doc['sha256']==expected['document_hash'] and
                    int(datetime.fromisoformat(decision['created_at']).timestamp())==expected['timestamp'] and
                    expected['outcome']==({'confirmed_fraud':1,'appeal_upheld':2}.get(decision['outcome'])))
        return (manifest['decision_id']==bundle['record_id'] and
                int(datetime.fromisoformat(manifest['timestamp']).timestamp())==expected['timestamp'] and
                expected['outcome']==({'confirmed_fraud':1,'appeal_upheld':2}.get(manifest['outcome'])))
    except (KeyError,TypeError,ValueError):return False


def check_chain(bundle,rpc):
    result=dict(state='unavailable',detail='The ledger RPC or contract is not configured.',checked_at=datetime.now().astimezone().isoformat())
    if not rpc or not bundle.get('contract'):return result
    if not bundle.get('transaction_hash'):return {**result,'state':'pending','detail':'No transaction receipt is available yet.'}
    try:
        w3=Web3(Web3.HTTPProvider(rpc,request_kwargs={'timeout':12}))
        if w3.eth.chain_id!=bundle['chain_id']:return {**result,'state':'mismatch','detail':'RPC chain ID does not match the recorded network.'}
        address=Web3.to_checksum_address(bundle['contract'])
        if not w3.eth.get_code(address):return {**result,'state':'mismatch','detail':'No ledger contract code exists at the recorded address.'}
        contract=w3.eth.contract(address=address,abi=json.loads(Path(__file__).with_name('ledger_abi.json').read_text()))
        expected=bundle['expected_record']
        record=contract.functions.records(bytes.fromhex(expected['record_id'][2:])).call()
        actual={key:Web3.to_hex(record[i]) for i,key in enumerate(['case_id','document_hash','evidence_hash','parent_record_id'])}
        actual.update(timestamp=int(record[4]),outcome=int(record[5]))
        receipt=w3.eth.get_transaction_receipt(bundle['transaction_hash'])
        transaction=w3.eth.get_transaction(bundle['transaction_hash'])
        event_matches=False
        event_keys={'recordId':'record_id','caseId':'case_id','documentHash':'document_hash','evidenceHash':'evidence_hash','parentRecordId':'parent_record_id','timestamp':'timestamp','outcome':'outcome'}
        for log in receipt.logs:
            if log['address'].lower()!=address.lower():continue
            try:
                event=contract.events.DecisionAnchored().process_log(log)['args']
                event_matches=all((Web3.to_hex(event[key]) if key not in ['timestamp','outcome'] else int(event[key]))==expected[field] for key,field in event_keys.items())
                if event_matches:break
            except Exception:continue
        block=w3.eth.get_block(receipt.blockNumber)
        canonical_block=Web3.to_hex(block.hash)==Web3.to_hex(receipt.blockHash)
        matches=bool(receipt.status==1 and transaction['to'] and transaction['to'].lower()==address.lower() and canonical_block and event_matches and all(actual[k]==expected[k] for k in actual))
        result.update(state='match' if matches else 'mismatch',detail='Successful receipt, emitted event and stored contract record match the expected hashes and decision.' if matches else 'Receipt, block, event or contract data does not match this audit record.',
                      block_number=receipt.blockNumber,block_hash=Web3.to_hex(receipt.blockHash),transaction_hash=Web3.to_hex(receipt.transactionHash),
                      writer=transaction['from'],confirmations=max(0,w3.eth.block_number-receipt.blockNumber+1),actual_record=actual)
    except TransactionNotFound:result.update(state='pending',detail='The transaction has no available receipt on the configured chain.')
    except Exception:result['detail']='Ledger read failed or returned unsupported data. No match was inferred; retry or verify through your own RPC.'
    return result
