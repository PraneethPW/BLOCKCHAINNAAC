"""Clear results must preserve the difference between processing and acceptance."""
import io
from sqlalchemy import select
from pypdf import PdfReader
import main
import verification
from test_workflow import account,upload


def test_completed_check_review_and_changed_original_have_consistent_results(client):
    owner=account(client);reviewer=account(client,'reviewer@example.com','reviewer')
    original=b'Annual institutional report: 100 students placed.'
    document=upload(client,owner,original);endpoint='/documents/'+document['id']
    client.post(endpoint+'/verify',headers=owner);verification.process_next()
    data=client.get(endpoint,headers=owner).json()
    response=data['verification_response']
    assert response['analysis_complete'] and response['code']=='issuer_evidence_required'
    assert response['acceptance']=='not_verified' and response['action']
    assert response['title']=='Neutral' and response['outcome']=='neutral'
    assert response['mode']=='automated' and 'pending' not in response['reason'].lower()
    assert data['job']['result']['automated_assessment']['outcome']=='neutral'
    assert data['status']=='unverified' and client.get('/ledger',headers=owner).json()==[]
    result=client.post('/trusted-records',headers=reviewer,data={'college':'Test College','category':'Student placements','period':'2025-26','issuer':'Test Employer','reference':'Authorized isolated test source REF-100'},files={'file':('issuer.txt',original,'text/plain')})
    assert result.status_code==201
    client.post(endpoint+'/verify',headers=owner);verification.process_next()
    automatic=client.get(endpoint,headers=owner).json()
    assert automatic['verification_response']['acceptance']=='accepted'
    assert automatic['verification_response']['outcome']=='genuine'
    assert automatic['status']=='verified' and automatic['decisions']==[]
    assert automatic['job']['result']['automated_assessment']['outcome']=='genuine'
    assert client.get('/ledger',headers=owner).json()==[]
    assert any(e['kind']=='assessment' and e['title'].startswith('Genuine') for e in automatic['activity'])
    assert client.get('/accreditation',headers=owner).json()['dossiers'][0]['documents'][0]['verification_response']==automatic['verification_response']
    reviewed=client.post(endpoint+'/decisions',headers=reviewer,json={'outcome':'verified','reason':'An intact authorized issuer original supports this institutional submission.','evidence':'Authorized source REF-100 and original fingerprint comparison'})
    assert reviewed.status_code==200,reviewed.text
    response=reviewed.json()['verification_response']
    assert response['code']=='reviewer_verified' and response['acceptance']=='accepted'
    assert client.get('/documents',headers=owner).json()[0]['verification_response']==response
    report=client.get(endpoint+'/report',headers=owner)
    assert response['title'] in '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(report.content)).pages)
    with main.SessionLocal() as s:
        stored=s.get(main.Document,document['id']);(main.STORAGE/stored.storage_name).write_bytes(b'Changed institutional count: 40 placements.')
    client.post(endpoint+'/verify',headers=owner);verification.process_next()
    changed=client.get(endpoint,headers=owner).json()
    assert changed['decisions'][-1]['outcome']=='verified'
    assert changed['verification_response']['code']=='integrity_failed'
    assert changed['verification_response']['acceptance']=='blocked'
    assert changed['verification_response']['outcome']=='manipulated'
    assert changed['verification_response']['title']=='Manipulated — stored file changed'


def test_invalid_pdf_parser_failure_is_reported_as_corrupted_without_fraud(client):
    owner=account(client)
    uploaded=client.post('/documents?background=true',headers=owner,data={'category':'Research publications','period':'2026'},files={'file':('unreadable.pdf',b'%PDF-1.7\ninvalid objects\n%%EOF','application/pdf')})
    assert uploaded.status_code==201
    assert uploaded.json()['verification_response']['acceptance']=='processing'
    verification.process_next()
    result=client.get('/documents/'+uploaded.json()['id'],headers=owner).json()
    assert result['job']['state']=='failed'
    assert result['verification_response']['code']=='corrupted_file'
    assert result['verification_response']['outcome']=='corrupted'
    assert result['verification_response']['acceptance']=='blocked'
    assert client.get('/ledger',headers=owner).json()==[]


def test_locked_pdf_is_neutral_not_corrupted_or_fake(client):
    from pypdf import PdfWriter
    owner=account(client)
    pdf=PdfWriter();pdf.add_blank_page(width=300,height=300);pdf.encrypt('private-password')
    original=io.BytesIO();pdf.write(original)
    uploaded=client.post('/documents?background=true',headers=owner,data={'category':'Financial records','period':'2026'},files={'file':('locked.pdf',original.getvalue(),'application/pdf')})
    verification.process_next()
    result=client.get('/documents/'+uploaded.json()['id'],headers=owner).json()
    assert result['job']['result']['failure_category']=='limited'
    assert result['verification_response']['title']=='Neutral'
    assert result['verification_response']['outcome']=='neutral'
    assert 'encrypted' in result['verification_response']['reason']


def test_processing_outage_remains_neutral(client,monkeypatch):
    owner=account(client);document=upload(client,owner)
    def failed(*args):raise RuntimeError('Inspection service is temporarily unavailable.')
    monkeypatch.setattr(verification,'inspect_bytes',failed)
    client.post('/documents/'+document['id']+'/verify',headers=owner);verification.process_next()
    result=client.get('/documents/'+document['id'],headers=owner).json()
    assert result['job']['result']['failure_category']=='processing'
    assert result['verification_response']['outcome']=='neutral'
    assert result['job']['result']['automated_assessment']['outcome']=='neutral'
    assert 'unavailable' in result['verification_response']['reason']
    assert result['decisions']==[] and client.get('/ledger',headers=owner).json()==[]


def test_source_tamper_revokes_automatic_match_without_faking_a_fraud_decision(client):
    owner=account(client);reviewer=account(client,'reviewer@example.com','reviewer');document=upload(client,owner)
    source=client.post('/trusted-records',headers=reviewer,data={'college':'Test College','category':'Student placements','period':'2025-26','issuer':'Test Employer','reference':'Independent original source REF-100'},files={'file':('issuer.txt',b'Claim: 100 placements; needs corroboration.','text/plain')})
    endpoint='/documents/'+document['id']
    client.post(endpoint+'/verify',headers=owner);verification.process_next()
    assert client.get(endpoint,headers=owner).json()['verification_response']['outcome']=='genuine'
    with main.SessionLocal() as s:
        registered=s.get(main.SourceRecord,source.json()['id']);(main.STORAGE/registered.storage_name).write_bytes(b'Changed issuer source')
    client.post(endpoint+'/recheck',headers=owner)
    result=client.get(endpoint,headers=owner).json()
    assert result['verification_response']['outcome']=='conflict'
    assert result['verification_response']['acceptance']=='blocked'
    assert result['status']!='verified' and result['decisions']==[]
    assert client.get('/ledger',headers=owner).json()==[]


def test_missing_stored_file_is_not_claimed_to_be_manipulated(client):
    owner=account(client);document=upload(client,owner);endpoint='/documents/'+document['id']
    with main.SessionLocal() as s:
        stored=s.get(main.Document,document['id']);(main.STORAGE/stored.storage_name).unlink()
    result=client.post(endpoint+'/recheck',headers=owner).json()
    assert result['verification_response']['outcome']=='conflict'
    assert 'missing' in result['verification_response']['reason']


def test_damaged_image_has_an_automatic_corruption_result(client):
    owner=account(client)
    uploaded=client.post('/documents?background=true',headers=owner,data={'category':'Infrastructure','period':'2026'},files={'file':('damaged.png',b'invalid image bytes','image/png')})
    assert uploaded.status_code==201
    verification.process_next()
    result=client.get('/documents/'+uploaded.json()['id'],headers=owner).json()
    assert result['verification_response']['outcome']=='corrupted'
    assert result['job']['result']['automated_assessment']['outcome']=='corrupted'


def test_explicit_fiction_is_non_genuine_without_confirming_fraud(client):
    owner=account(client)
    document=upload(client,owner,b'Fictional document\nPlacement evidence created for demonstration only.\n100 students placed.')
    endpoint='/documents/'+document['id']
    client.post(endpoint+'/verify',headers=owner);verification.process_next()
    result=client.get(endpoint,headers=owner).json()
    assert result['verification_response']['outcome']=='fabricated'
    assert result['verification_response']['acceptance']=='blocked'
    assert result['verification_response']['mode']=='automated'
    assert result['decisions']==[] and client.get('/ledger',headers=owner).json()==[]


def test_old_source_match_requires_current_inspection_before_auto_genuine(client):
    import json
    owner=account(client);reviewer=account(client,'reviewer@example.com','reviewer');document=upload(client,owner)
    client.post('/trusted-records',headers=reviewer,data={'college':'Test College','category':'Student placements','period':'2025-26','issuer':'Test Employer','reference':'Independent original source REF-100'},files={'file':('issuer.txt',b'Claim: 100 placements; needs corroboration.','text/plain')})
    with main.SessionLocal() as s:
        stored=s.get(main.Document,document['id'])
        main.run_checks(stored,s)
        s.add(main.VerificationJob(document_id=stored.id,state='complete',progress=100,result=json.dumps({'engine_version':'3.1'})))
        s.commit()
    result=client.get('/documents/'+document['id'],headers=owner).json()
    assert result['verification_response']['outcome']=='neutral'
    assert result['verification_response']['code']=='checks_required'
    assert result['status']!='verified'
