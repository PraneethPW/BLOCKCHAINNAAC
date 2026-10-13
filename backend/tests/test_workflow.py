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
    c.cookies.clear()
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
    client.cookies.clear()
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
    # Acceptance on appeal needs current processing and an exact issuer source.
    assert client.post('/trusted-records',headers=reviewer,data={'college':'Test College','category':'Student placements','period':'2025-26','issuer':'Test Issuer','reference':'Authorized appeal source REF-456'},files={'file':('issuer.txt',b'Claim: 100 placements; needs corroboration.','text/plain')}).status_code==201
    assert client.post(f"/documents/{d['id']}/verify",headers=owner).status_code==202
    import verification
    verification.process_next()
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

def test_cookie_session_csrf_logout_and_password_revocation(client):
    h=account(client)
    assert client.get('/auth/me').status_code==200
    assert client.post('/auth/logout').status_code==403
    assert client.post('/auth/logout',headers={'X-Veris-Request':'workspace','Origin':'https://untrusted.example'}).status_code==403
    assert client.post('/auth/logout',headers={'X-Veris-Request':'workspace'}).status_code==200
    assert client.get('/auth/me',headers=h).status_code==401
    login=client.post('/auth/login',json={'email':'college@example.com','password':'test-password-long'})
    token={'Authorization':'Bearer '+login.json()['token']}
    assert 'HttpOnly' in login.headers['set-cookie'] and 'SameSite=lax' in login.headers['set-cookie']
    changed=client.post('/auth/password',headers=token,json={'current_password':'test-password-long','new_password':'new-passphrase-long-enough'})
    assert changed.status_code==200
    assert client.get('/auth/me',headers=token).status_code==401
    assert client.post('/auth/login',json={'email':'college@example.com','password':'test-password-long'}).status_code==401
    assert client.post('/auth/login',json={'email':'college@example.com','password':'new-passphrase-long-enough'}).status_code==200

def test_invitation_is_single_use_and_invalid_invite_rolls_back(client):
    from datetime import datetime,timedelta,timezone
    code='test-only-reviewer-invitation'
    with main.SessionLocal() as s:
        s.add(main.ReviewerInvite(digest=hashlib.sha256(code.encode()).hexdigest(),expires=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()));s.commit()
    body={'email':'reviewer@example.com','password':'reviewer-passphrase-long','name':'Reviewer','college':'Review Institution','reviewer_invite':code}
    assert client.post('/auth/register',json=body).json()['role']=='reviewer'
    assert client.post('/auth/register',json={**body,'email':'second@example.com'}).status_code==403
    with main.SessionLocal() as s:assert not s.scalar(select(main.Account).where(main.Account.email=='second@example.com'))

def test_durable_job_and_archive_visibility(client,monkeypatch):
    import verification
    async def title_search(title,on_result):return [],[]
    monkeypatch.setattr(verification,'discover_title',title_search)
    owner=account(client)
    r=client.post('/documents?background=true',headers=owner,data={'category':'Research publications','period':'2026'},files={'file':('original.txt',b'Original public research evidence without a DOI.','text/plain')})
    assert r.status_code==201 and r.json()['job']['state']=='queued'
    d=r.json()
    assert client.post('/documents/'+d['id']+'/verify',headers=owner).status_code==409
    verification.process_next()
    result=client.get('/documents/'+d['id'],headers=owner).json()
    assert result['job']['state']=='complete' and result['job']['progress']==100
    stages=[entry['stage'] for entry in result['job']['timeline']]
    assert stages[0]=='Inspecting original file integrity'
    assert 'Classifying document type' in stages
    assert stages[-1].startswith('Automatic assessment:')
    assert result['job']['result']['metadata']['classification']['version']=='1.0'
    assert result['status']=='unverified' and result['job']['result']['sources']==[]
    before=client.get('/workspace',headers=owner).json()
    assert before['total']==1
    with main.SessionLocal() as s:s.add(main.Archive(id=d['id'],kind='document',reason='Isolated QA record'));s.commit()
    assert client.get('/workspace',headers=owner).json()['total']==0
    assert client.get('/documents/'+d['id'],headers=owner).status_code==404

def test_stored_original_integrity_failure_is_retained(client):
    import verification
    h=account(client)
    r=client.post('/documents?background=true',headers=h,data={'category':'Research publications','period':'2026'},files={'file':('original.txt',b'Original evidence.','text/plain')})
    id=r.json()['id']
    with main.SessionLocal() as s:
        doc=s.get(main.Document,id);(main.STORAGE/doc.storage_name).write_bytes(b'changed bytes')
    verification.process_next()
    result=client.get('/documents/'+id,headers=h).json()
    assert result['job']['state']=='failed' and 'fingerprint differs' in result['job']['error']
    assert result['status']=='flagged'
    assert result['job']['result']['assessment']['state']=='conflicting_evidence'
    assert client.post('/documents/'+id+'/recheck',headers=h).json()['status']=='flagged'
    assert client.get('/ledger',headers=h).json()==[]

def test_workspace_search_pagination_and_ledger_isolation(client):
    h=account(client)
    with main.SessionLocal() as s:
        u=s.scalar(select(main.Account).where(main.Account.email=='college@example.com'))
        for i in range(101):s.add(main.Document(owner_id=u.id,filename=f'evidence-{i:03}.txt',college=u.college,category='Research publications',period='2026',sha256=hashlib.sha256(str(i).encode()).hexdigest(),storage_name=f'isolated-{i}.txt',text='Isolated test text'))
        s.commit()
    first=client.get('/workspace',headers=h).json()
    second=client.get('/workspace?offset=100',headers=h).json()
    assert first['total']==101 and first['matching']==101 and len(first['documents'])==100
    assert len(second['documents'])==1 and first['documents'][0]['id']!=second['documents'][0]['id']
    assert client.get('/workspace?search=evidence-050',headers=h).json()['matching']==1
    assert client.get('/workspace?status=confirmed_fraud',headers=h).json()['matching']==0
    other=account(client,'other@example.com')
    assert client.get('/workspace',headers=other).json()['total']==0
    assert client.get('/ledger',headers=other).json()==[]
