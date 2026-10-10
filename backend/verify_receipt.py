"""Verify an exported proof through an independently selected read-only RPC.

Usage: python verify_receipt.py proof.json --rpc YOUR_RPC [--document ORIGINAL]
No wallet, application credentials or transactions are needed.
"""
import argparse
import hashlib
import json
from pathlib import Path
from ledger_proof import payload_binding,check_chain

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('proof',type=Path)
    parser.add_argument('--rpc',required=True,help='Use your own endpoint for the recorded network.')
    parser.add_argument('--document',type=Path,help='Optionally hash your locally held original without uploading it.')
    args=parser.parse_args()
    bundle=json.loads(args.proof.read_text(encoding='utf-8'))
    bound=payload_binding(bundle)
    chain=check_chain(bundle,args.rpc) if bound else {'state':'mismatch','detail':'The snapshot and expected on-chain fields are inconsistent.'}
    document_match=None if not args.document else '0x'+hashlib.sha256(args.document.read_bytes()).hexdigest()==bundle['expected_record']['document_hash']
    ok=bound and chain['state']=='match' and document_match is not False
    print(json.dumps(dict(audit_integrity_matches=ok,snapshot_binding_matches=bound,local_document_matches=document_match,chain_check=chain,scope=bundle.get('snapshot_scope'),trust_model=bundle.get('trust_model')),indent=2))
    raise SystemExit(0 if ok else 1)
