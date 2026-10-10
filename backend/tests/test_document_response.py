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
    assert 'issuer evidence required' in response['title']
    assert data['status']=='unverified' and client.get('/ledger',headers=owner).json()==[]
    result=client.post('/trusted-records',headers=reviewer,data={'college':'Test College','category':'Student placements','period':'2025-26','issuer':'Test Employer','reference':'Authorized isolated test source REF-100'},files={'file':('issuer.txt',original,'text/plain')})
    assert result.status_code==201
    client.post(endpoint+'/verify',headers=owner);verification.process_next()
    assert client.get(endpoint,headers=owner).json()['verification_response']['acceptance']=='awaiting_review'
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
    assert changed['verification_response']['title']=='Stored original has changed'


def test_processing_failure_is_not_a_guessed_fraud_or_corruption_verdict(client):
    owner=account(client)
    uploaded=client.post('/documents?background=true',headers=owner,data={'category':'Research publications','period':'2026'},files={'file':('unreadable.pdf',b'%PDF-1.7\ninvalid objects\n%%EOF','application/pdf')})
    assert uploaded.status_code==201
    assert uploaded.json()['verification_response']['acceptance']=='processing'
    verification.process_next()
    result=client.get('/documents/'+uploaded.json()['id'],headers=owner).json()
    assert result['job']['state']=='failed'
    assert result['verification_response']['code']=='check_failed'
    assert result['verification_response']['acceptance']=='blocked'
    assert client.get('/ledger',headers=owner).json()==[]
