"""Read-only local wallet diagnosis. Never prints credentials or submits transactions."""
import argparse,json,os
from collections import Counter
from pathlib import Path
from dotenv import load_dotenv

def diagnose(check_network=False):
    from sqlalchemy import inspect,select,text
    from main import engine,SessionLocal,STORAGE,Document
    from wallet import WalletDocument,config
    result={'services':config(),'upload_directory':str(STORAGE),'database':{'connected':False}}
    try:
        with engine.connect() as connection:connection.execute(text('SELECT 1'))
        result['database']['connected']=True
        with SessionLocal() as session:
            entries=list(session.scalars(select(WalletDocument))) if inspect(engine).has_table('veris_wallet_documents') else []
            result['wallet_records']=dict(states=dict(Counter(e.state for e in entries)),networks=dict(Counter(e.network for e in entries)),with_cid=sum(bool(e.cid) for e in entries),with_transaction=sum(bool(e.tx_hash) for e in entries))
            pending=[e for e in entries if e.state in ['queued','pinning','pinned','broadcast','failed']]
            missing=0
            for entry in pending:
                original=session.get(Document,entry.document_id)
                if not original or not (STORAGE/original.storage_name).is_file():missing+=1
            result['wallet_records']['pending_original_files_missing']=missing
    except Exception:
        result['database']['error']='Database connection or wallet record lookup failed. Check DATABASE_URL and network access privately.'
    if check_network:
        from wallet_worker import chain,artifact
        from web3 import Web3
        network=result['services']['network']
        try:
            web3,chain_id=chain(network)
            check={'chain_id':chain_id,'connected':True}
            contract_address=os.getenv('VAULT_CONTRACT_ADDRESS','') if network=='sepolia' else ''
            if contract_address:
                check['contract_deployed']=bool(web3.eth.get_code(Web3.to_checksum_address(contract_address)))
                if check['contract_deployed']:
                    contract=web3.eth.contract(address=Web3.to_checksum_address(contract_address),abi=artifact()['abi'])
                    writer=contract.functions.writer().call()
                    key=os.getenv('VAULT_PRIVATE_KEY' if network=='sepolia' else 'LEDGER_PRIVATE_KEY','')
                    check['configured_signer_matches_contract']=web3.eth.account.from_key(key).address==writer if key else None
                    check['writer_balance_wei']=web3.eth.get_balance(writer)
                    check['writer_has_gas_funds']=check['writer_balance_wei']>0
            result['network_check']=check
        except Exception:
            result['network_check']={'connected':False,'error':'RPC, network, contract or signer validation failed. Check the named backend settings privately.'}
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',default='.env')
    parser.add_argument('--check-network',action='store_true',help='Read chain, contract writer and test-gas balance; no transactions.')
    args=parser.parse_args()
    path=Path(args.env_file)
    if not path.is_file():parser.error('The specified environment file does not exist.')
    load_dotenv(path)
    print(json.dumps(diagnose(args.check_network),indent=2))
