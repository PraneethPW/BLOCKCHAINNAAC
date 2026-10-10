"""Claims must be corroborated; audit evidence must survive database tampering."""
import hashlib
import json
from sqlalchemy import select
import main
import accreditation
from ledger_proof import payload_binding
from test_workflow import account, upload


def declare(client, owner, doc, quantity=100, issuer='Test Employer'):
    result=client.post('/accreditation/claims',headers=owner,json={
        'document_id':doc['id'],'criterion':'Placement evidence',
        'statement':'The institution reports 100 students placed in this reporting period.',
        'issuer':issuer,'quantity':quantity})
    assert result.status_code==201,result.text
    return result.json()['id']


def register_source(client, reviewer, content, count=100):
    result=client.post('/trusted-records',headers=reviewer,data={
        'college':'Test College','category':'Student placements','period':'2025-26',
        'issuer':'Test Employer','reference':'Authorized test-only employer response REF-100',
        'placements':str(count)},files={'file':('issuer.txt',content,'text/plain')})
    assert result.status_code==201,result.text
    return result.json()


def latest_claim(client, owner):
    return client.get('/accreditation',headers=owner).json()['dossiers'][0]['claims'][-1]


def support(client, reviewer, claim):
    return client.post(f'/accreditation/claims/{claim}/reviews',headers=reviewer,json={
        'outcome':'supported','reason':'Current authorized issuer evidence supports the precise institutional count.',
        'evidence':'Employer response REF-100 and intact original comparison'})


def test_claim_count_and_declared_issuer_gate_acceptance(client):
    owner=account(client);reviewer=account(client,'reviewer@example.com','reviewer')
    content=b'Annual report: 100 students placed.'
    doc=upload(client,owner,content);claim=declare(client,owner,doc)
    assert latest_claim(client,owner)['comparison']['state']=='issuer_evidence_needed'
    assert support(client,reviewer,claim).status_code==409
    revision=client.get('/workspace',headers=owner).json()['revision']
    source=register_source(client,reviewer,content)
    assert client.get('/workspace',headers=owner).json()['revision']!=revision
    assert client.post(f"/documents/{doc['id']}/verify",headers=owner).status_code==202
    import verification
    verification.process_next()
    accepted=client.post(f"/documents/{doc['id']}/decisions",headers=reviewer,json={
        'outcome':'verified','reason':'Current checks and an authorized identical issuer original support acceptance.',
        'evidence':'Issuer response REF-100, exact original SHA-256 comparison'})
    assert accepted.status_code==200,accepted.text
    assert support(client,reviewer,claim).status_code==200
    wrong_count=declare(client,owner,doc,quantity=40)
    comparison=latest_claim(client,owner)['comparison']
    assert comparison['state']=='claim_conflict' and comparison['document_quantities']==[100]
    assert comparison['issuer_quantities']==[100] and not comparison['eligible']
    assert support(client,reviewer,wrong_count).status_code==409
    wrong_issuer=declare(client,owner,doc,issuer='Unconnected Employer')
    assert support(client,reviewer,wrong_issuer).status_code==409
    with main.SessionLocal() as s:
        registered=s.get(main.SourceRecord,source['id'])
        (main.STORAGE/registered.storage_name).write_bytes(b'Altered issuer original')
    assert support(client,reviewer,claim).status_code==409
    first=client.get('/accreditation',headers=owner).json()['dossiers'][0]['claims'][0]
    assert first['status']=='supported' and not first['comparison']['eligible']
    assert first['comparison']['state']=='source_integrity_conflict'
    assert client.get('/ledger',headers=owner).json()==[]


def test_claim_isolation_immutable_submission_and_review_history(client):
    owner=account(client);doc=upload(client,owner);claim=declare(client,owner,doc)
    other=account(client,'other@example.com');reviewer=account(client,'reviewer@example.com','reviewer')
    assert client.get('/accreditation',headers=other).json()['dossiers']==[]
    body={'document_id':doc['id'],'criterion':'Placements','statement':'Another account cannot submit this institutional claim.','issuer':'Test Employer','quantity':100}
    assert client.post('/accreditation/claims',headers=other,json=body).status_code==404
    assert client.post('/accreditation/claims',headers=reviewer,json=body).status_code==403
    assert client.put(f'/accreditation/claims/{claim}',headers=owner,json=body).status_code in (404,405)
    for outcome in ['clarification_required','insufficient_evidence']:
        result=client.post(f'/accreditation/claims/{claim}/reviews',headers=reviewer,json={
            'outcome':outcome,'reason':'Independent issuer records are required to substantiate this specific claim.',
            'evidence':'Request for authorized employer response REF-100'})
        assert result.status_code==200,result.text
    assert len(latest_claim(client,owner)['reviews'])==2
    assert latest_claim(client,owner)['status']=='insufficient_evidence'
    assert client.get('/ledger',headers=owner).json()==[]


def confirmed(client):
    owner=account(client);reviewer=account(client,'reviewer@example.com','reviewer')
    doc=upload(client,owner,b'Annual report: 100 students placed.')
    claim=declare(client,owner,doc)
    source=register_source(client,reviewer,b'Independent issuer response: 40 students placed.',40)
    result=client.post(f"/documents/{doc['id']}/decisions",headers=reviewer,json={
        'outcome':'confirmed_fraud','reason':'Isolated regression case: investigated issuer evidence contradicts the institutional count.',
        'evidence':'Test-only employer denial REF-40 and documented reviewer investigation'})
    assert result.status_code==200,result.text
    anchor=client.get('/ledger',headers=owner).json()[0]
    return owner,reviewer,doc,claim,source,anchor


def test_snapshot_seals_claim_sources_and_decision_and_is_owner_only(client,monkeypatch):
    owner,reviewer,doc,claim,source,anchor=confirmed(client)
    proof=client.get(f"/ledger/{anchor['id']}/proof-file",headers=owner).json()
    assert payload_binding(proof)
    manifest=json.loads(proof['canonical_payload'])
    assert manifest['claims'][0]['id']==claim
    assert manifest['issuer_records'][0]['placement_count']==40
    assert manifest['document']['id']==doc['id']
    with main.SessionLocal() as s:
        assert s.get(main.Anchor,anchor['id']).evidence_hash==hashlib.sha256(proof['canonical_payload'].encode()).hexdigest()
    import ledger_proof
    monkeypatch.setattr(ledger_proof,'check_chain',lambda *args:{'state':'match','detail':'Isolated RPC fixture'})
    result=client.get(f"/ledger/{anchor['id']}/proof",headers=owner).json()
    assert result['verified'] and result['snapshot_binding_matches']
    other=account(client,'other@example.com')
    assert client.get(f"/ledger/{anchor['id']}/proof-file",headers=other).status_code==404
    assert client.get(f"/ledger/{anchor['id']}/proof",headers=other).status_code==404
    with main.SessionLocal() as s:
        s.get(main.AccreditationClaim,claim).statement='Database edit after the evidence was sealed on chain.'
        s.commit()
    result=client.get(f"/ledger/{anchor['id']}/proof",headers=owner).json()
    assert result['snapshot_binding_matches'] and not result['verified']
    assert not result['claim_context_matches_snapshot']


def test_snapshot_digest_context_and_current_source_tampering(client,monkeypatch):
    owner,_,doc,_,source,anchor=confirmed(client)
    import ledger_proof
    monkeypatch.setattr(ledger_proof,'check_chain',lambda *args:{'state':'match','detail':'Isolated RPC fixture'})
    with main.SessionLocal() as s:
        s.get(main.Document,doc['id']).period='2030-31'
        s.scalar(select(main.SourceMetric).where(main.SourceMetric.source_id==source['id'])).value=100
        s.get(main.Decision,anchor['id']).reason='Edited reviewer narrative after sealing'
        s.commit()
    result=client.get(f"/ledger/{anchor['id']}/proof",headers=owner).json()
    assert not result['verified'] and result['snapshot_matches_ledger_digest']
    assert not result['document_context_matches_snapshot'] and not result['current_decision_matches_snapshot']
    assert not result['issuer_source_integrity'][0]['intact']
    with main.SessionLocal() as s:
        snapshot=s.get(main.EvidenceSnapshot,anchor['id'])
        data=json.loads(snapshot.payload);data['claims'][0]['quantity']=40
        snapshot.payload=main.canonical(data);s.commit()
    result=client.get(f"/ledger/{anchor['id']}/proof",headers=owner).json()
    assert not result['snapshot_matches_ledger_digest'] and not result['snapshot_binding_matches']
    with main.SessionLocal() as s:
        s.get(main.EvidenceSnapshot,anchor['id']).payload='corrupt snapshot bytes';s.commit()
    assert client.get(f"/ledger/{anchor['id']}/proof",headers=owner).status_code==409


def test_replaced_original_and_database_hash_cannot_match_anchored_fingerprint(client,monkeypatch):
    owner,_,doc,_,_,anchor=confirmed(client)
    import ledger_proof
    monkeypatch.setattr(ledger_proof,'check_chain',lambda *args:{'state':'match','detail':'Isolated RPC fixture'})
    with main.SessionLocal() as s:
        stored=s.get(main.Document,doc['id']);content=b'Replaced file with altered claims'
        (main.STORAGE/stored.storage_name).write_bytes(content)
        stored.sha256=hashlib.sha256(content).hexdigest();s.commit()
    result=client.get(f"/ledger/{anchor['id']}/proof",headers=owner).json()
    assert not result['verified'] and not result['original_matches_submitted_digest']


def test_legacy_receipts_do_not_invent_historical_evidence(client):
    owner,_,doc,_,_,anchor=confirmed(client)
    with main.SessionLocal() as s:
        decision=s.get(main.Decision,anchor['id'])
        old_payload=main.canonical({'decision_id':decision.id,'reason':decision.reason,'evidence':decision.evidence,'reviewer_id':decision.reviewer_id,'outcome':decision.outcome,'timestamp':decision.created_at})
        s.get(main.Anchor,anchor['id']).evidence_hash=hashlib.sha256(old_payload.encode()).hexdigest()
        s.delete(s.get(main.EvidenceSnapshot,anchor['id']));s.commit()
    proof=client.get(f"/ledger/{anchor['id']}/proof-file",headers=owner).json()
    assert payload_binding(proof)
    assert proof['snapshot_scope'].startswith('Legacy decision narrative only')
    assert proof['claim_context_matches_snapshot'] is None and proof['issuer_source_integrity']==[]
    assert 'issuer_records' not in json.loads(proof['canonical_payload'])
