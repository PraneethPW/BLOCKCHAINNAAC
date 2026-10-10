import os
import tempfile
import hashlib
import sys
from pathlib import Path
import pytest

scratch=tempfile.TemporaryDirectory()
os.environ['DATABASE_URL']='sqlite:///'+str(Path(scratch.name)/'test.db')
os.environ['UPLOAD_DIR']=str(Path(scratch.name)/'uploads')
os.environ['APP_ENV']='test'
os.environ['JWT_SECRET']='unit-test-secret-32-characters-minimum'
sys.path.insert(0,str(Path(__file__).parent.parent))
from fastapi.testclient import TestClient
from sqlalchemy import select
import main

@pytest.fixture()
def client():
    main.Base.metadata.drop_all(main.engine)
    main._limits.clear()
    with TestClient(main.app) as c:yield c

@pytest.fixture(scope='session',autouse=True)
def dispose_at_end():
    yield
    main.engine.dispose()
    scratch.cleanup()

def account(c,email='college@example.com',role='college'):
    response=c.post('/auth/register',json={'email':email,'password':'test-password-long','name':'Test User','college':'Test College'})
    assert response.status_code==201,response.text
    if role=='reviewer':
        with main.SessionLocal() as s:
            u=s.scalar(select(main.Account).where(main.Account.email==email));u.role='reviewer';s.commit()
    login=c.post('/auth/login',json={'email':email,'password':'test-password-long'})
    return {'Authorization':'Bearer '+login.json()['token']}
def upload(c,h,content=b'Claim: 100 placements; needs corroboration.'):
    r=c.post('/documents',headers=h,data={'category':'Student placements','period':'2025-26'},files={'file':('report.txt',content,'text/plain')})
    assert r.status_code==201,r.text
    return r.json()

def test_upload_does_not_establish_authenticity(client):
    h=account(client);d=upload(client,h)
    assert d['status']=='unverified'
    assert d['sha256']==hashlib.sha256(b'Claim: 100 placements; needs corroboration.').hexdigest()
    assert any(c['name']=='Authorized source comparison' and c['state']=='unknown' for c in d['checks'])
    duplicate=upload(client,h)
    assert duplicate['status']=='flagged'
    assert client.get('/ledger',headers=h).json()==[]

def test_owner_isolation_and_reviewer_permission(client):
    a=account(client);d=upload(client,a);b=account(client,'other@example.com')
    assert client.get('/documents',headers=b).json()==[]
    for endpoint in ['', '/file','/report']:
        assert client.get('/documents/'+d['id']+endpoint,headers=b).status_code==404
    assert client.get('/documents').status_code==401
    assert client.post(f"/documents/{d['id']}/decisions",headers=a,json={'outcome':'confirmed_fraud','reason':'This is a deliberate test finding with evidence.','evidence':'issuer response TEST-01'}).status_code==403

def test_review_and_appeal_are_append_only(client):
    owner=account(client);reviewer=account(client,'reviewer@example.com','reviewer');d=upload(client,owner)
    endpoint=f"/documents/{d['id']}/decisions"
    body={'outcome':'confirmed_fraud','reason':'Issuer denial and investigation establish this sample finding.','evidence':'Authorized issuer denial REF-123'}
    assert client.post(endpoint,headers=reviewer,json={**body,'evidence':''}).status_code==400
    assert client.post(endpoint,headers=reviewer,json=body).status_code==200
    assert client.post(endpoint,headers=reviewer,json=body).status_code==409
    anchors=client.get('/ledger',headers=reviewer).json()
    assert len(anchors)==1 and anchors[0]['state'].startswith('Queued') and not anchors[0]['tx_hash']
    assert 'reason' not in anchors[0] and 'filename' not in anchors[0]
    assert client.post(f"/documents/{d['id']}/recheck",headers=reviewer).json()['status']=='confirmed_fraud'
    appeal=client.post(endpoint,headers=reviewer,json={'outcome':'appeal_upheld','reason':'An appeal produced new authorized records overturning the finding.','evidence':'Appeal evidence REF-456'})
    assert appeal.json()['status']=='verified'
    assert len(appeal.json()['decisions'])==2
    assert len(client.get('/ledger',headers=reviewer).json())==2
    assert client.post(endpoint,headers=reviewer,json={'outcome':'appeal_upheld','reason':'This appeal has no current confirmed finding.','evidence':'Reference 456'}).status_code==409
    pdf=client.get(f"/documents/{d['id']}/report",headers=owner)
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')

def test_source_match_requires_human_verification(client):
    h=account(client);r=account(client,'reviewer@example.com','reviewer');d=upload(client,h)
    response=client.post('/trusted-records',headers=r,data={'college':'Test College','category':'Student placements','period':'2025-26','issuer':'Test Employer','reference':'Authorized response ABC-123'},files={'file':('source.txt',b'Claim: 100 placements; needs corroboration.','text/plain')})
    assert response.status_code==201,response.text
    d=client.post(f"/documents/{d['id']}/recheck",headers=h).json()
    assert d['status']=='unverified'
    assert any(x['name']=='Authorized source comparison' and x['state']=='pass' for x in d['checks'])

def test_invalid_content_and_ai_consent(client,monkeypatch):
    h=account(client)
    response=client.post('/documents',headers=h,data={'category':'Student placements','period':'2025'},files={'file':('fake.pdf',b'not a pdf','application/pdf')})
    assert response.status_code==400
    d=upload(client,h)
    assert client.post(f"/documents/{d['id']}/ai",headers=h,json={'consent':False}).status_code==400
    monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
    assert client.post(f"/documents/{d['id']}/ai",headers=h,json={'consent':True}).status_code==503
    monkeypatch.setenv('OPENROUTER_API_KEY','test-key')
    monkeypatch.setenv('OPENROUTER_MODEL','paid-model')
    assert client.post(f"/documents/{d['id']}/ai",headers=h,json={'consent':True}).status_code==503

def test_ai_empty_reply_and_advice_do_not_change_status(client,monkeypatch):
    import httpx
    h=account(client);d=upload(client,h)
    monkeypatch.setenv('OPENROUTER_API_KEY','test-only-key')
    monkeypatch.setenv('OPENROUTER_MODEL','dots-studio/dots-3-note-preview:free')
    replies=[None,'Compare the reporting period and request issuer evidence.']
    class FreeProvider:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,headers,json):
            assert json['model'].endswith(':free')
            assert json['provider']['data_collection']=='deny'
            assert json['reasoning']['enabled'] is False
            return httpx.Response(200,json={'choices':[{'message':{'content':replies.pop(0)}}]})
    monkeypatch.setattr(main.httpx,'AsyncClient',FreeProvider)
    assert client.post(f"/documents/{d['id']}/ai",headers=h,json={'consent':True}).status_code==503
    response=client.post(f"/documents/{d['id']}/ai",headers=h,json={'consent':True})
    assert response.status_code==200 and response.json()['ai']
    assert response.json()['status']==d['status']

def test_independent_placement_count_mismatch(client):
    h=account(client);r=account(client,'reviewer@example.com','reviewer');d=upload(client,h,b'Annual report: 100 students placed.')
    result=client.post('/trusted-records',headers=r,data={'college':'Test College','category':'Student placements','period':'2025-26','issuer':'Authorized Employer','reference':'Verified placement records REF-40','placements':'40'},files={'file':('source.txt',b'Independent employer records: 40 students placed.','text/plain')})
    assert result.status_code==201,result.text
    checked=client.post(f"/documents/{d['id']}/recheck",headers=h).json()
    assert checked['status']=='flagged'
    count_check=next(c for c in checked['checks'] if c['name']=='Placement count comparison')
    assert count_check['state']=='warn' and '100' in count_check['detail'] and '40' in count_check['detail']
    assert client.get('/ledger',headers=r).json()==[]
