import asyncio
import io

import httpx
import pytest
from reportlab.pdfgen import canvas

import institutional_original as institutional
import verification
import main
from authenticity import assessment, finding
from test_workflow import account

URL='https://www.nirfindia.org/nirfpdfcdn/2025/pdf/Overall/IR-O-U-0456.pdf'
CATEGORIES=['Teaching & faculty','Research publications','Student placements','Infrastructure','Student outcomes','Financial records']


def report(identifier='IR-O-U-0456',year='2025',content='Submitted institutional record'):
    buf=io.BytesIO();pdf=canvas.Canvas(buf)
    lines=['National Institutional Ranking Framework','Ministry of Education','Government of India',
           f"Data Submitted by Institution for India Rankings '{year}'",
           f'Institute Name: Test Institute [{identifier}]',content]
    for i,line in enumerate(lines):pdf.drawString(40,780-i*30,line)
    pdf.save();return buf.getvalue()


def info(data):return verification.inspect_bytes(data,'.pdf')[1]


def transport(monkeypatch,handler):
    factory=httpx.AsyncClient
    monkeypatch.setattr(institutional.httpx,'AsyncClient',lambda **kw:factory(transport=httpx.MockTransport(handler),**kw))


def test_exact_source_identity_and_bytes_required(monkeypatch):
    original=report();transport(monkeypatch,lambda request:httpx.Response(200,content=original))
    match=asyncio.run(institutional.compare_institutional_original(original,info(original)))
    assert match['state']=='matched' and match['url']==URL
    assert match['source_sha256']==match['uploaded_sha256'] and match['checked_at']
    changed=report(content='Changed reported figures')
    assert asyncio.run(institutional.compare_institutional_original(changed,info(changed)))['state']=='different'
    checks=[finding('Official institutional original comparison','pass','Exact bytes')]
    assert assessment(checks)['file_verification_eligible']
    assert not assessment(checks)['verification_eligible']


@pytest.mark.parametrize('category',CATEGORIES)
def test_full_job_returns_genuine_file_for_each_category(client,monkeypatch,category):
    owner=account(client);original=report()
    transport(monkeypatch,lambda request:httpx.Response(200,content=original))
    async def no_records(*args):return []
    monkeypatch.setattr(verification,'corroborate',no_records)
    uploaded=client.post('/documents?background=true',headers=owner,data={'category':category,'period':'2025'},files={'file':('arbitrary.pdf',original,'application/pdf')})
    assert uploaded.status_code==201,uploaded.text
    verification.process_next()
    result=client.get('/documents/'+uploaded.json()['id'],headers=owner).json()
    assert result['job']['state']=='complete'
    assert result['verification_response']['code']=='institutional_match'
    assert result['verification_response']['outcome']=='genuine' and result['status']=='verified'
    assert not result['job']['result']['assessment']['verification_eligible']
    assert result['decisions']==[] and client.get('/ledger',headers=owner).json()==[]


@pytest.mark.parametrize('view',['detail','list'])
def test_polling_refreshes_document_and_job_in_same_snapshot(client,monkeypatch,view):
    owner=account(client);original=report()
    transport(monkeypatch,lambda request:httpx.Response(200,content=original))
    uploaded=client.post('/documents?background=true',headers=owner,data={'category':'Infrastructure','period':'2025'},files={'file':('original.pdf',original,'application/pdf')}).json()
    with main.SessionLocal() as reader:
        # Simulate a polling request loading the document just before the worker
        # commits its successful comparison in another session.
        stale=reader.get(main.Document,uploaded['id'])
        queued=reader.scalar(main.select(main.VerificationJob).where(main.VerificationJob.document_id==stale.id))
        assert queued.state=='queued' and stale.status=='unverified'
        verification.process_next()
        result=main.document_json(stale,reader) if view=='detail' else main.document_list_json([stale],reader)[0]
        assert result['job']['state']=='complete'
        assert result['job']['result']['institutional_original']['state']=='matched'
        assert result['verification_response']['outcome']=='genuine'
        assert result['status']=='verified'


@pytest.mark.parametrize('body',[b'<html>Unavailable</html>',report(identifier='IR-O-U-0220'),report(year='2024'),b'%PDF-broken'])
def test_bad_official_responses_cannot_authenticate(monkeypatch,body):
    transport(monkeypatch,lambda request:httpx.Response(200,content=body))
    original=report()
    assert asyncio.run(institutional.compare_institutional_original(original,info(original)))['state']=='unavailable'


def test_only_front_page_report_identity_selects_query(monkeypatch):
    def forbidden(**kw):raise AssertionError('Unrecognized records must not fetch URLs')
    monkeypatch.setattr(institutional.httpx,'AsyncClient',forbidden)
    for metadata in [dict(format='pdf',front_page_text='IR-O-U-0456 https://127.0.0.1/private'),dict(format='txt',front_page_text='')]:
        assert asyncio.run(institutional.compare_institutional_original(b'other',metadata))['state']=='not_applicable'
    front=info(report())['front_page_text']
    assert institutional.identity(front+'\nInstitute Name: Another [IR-O-U-0220]') is None


def test_redirect_allowlist_size_and_http_failure():
    requests=[]
    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ValueError):await institutional.download_original(client,URL)
        for response in [httpx.Response(503),httpx.Response(200,content=b'%PDF-'+b'x'*institutional.MAX_BYTES)]:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:response)) as client:
                with pytest.raises((ValueError,httpx.HTTPError)):await institutional.download_original(client,URL)
    asyncio.run(run());assert requests==[URL]
    for url in ['https://nirfindia.org.attacker.invalid/file','https://user@www.nirfindia.org/file','https://www.nirfindia.org:444/file']:
        assert not institutional.allowed(url)


def test_fictional_declaration_still_blocks_even_exact_file(client,monkeypatch):
    owner=account(client);original=report(content='fictional document')
    transport(monkeypatch,lambda request:httpx.Response(200,content=original))
    uploaded=client.post('/documents?background=true',headers=owner,data={'category':'Infrastructure','period':'2025'},files={'file':('declared.pdf',original,'application/pdf')})
    verification.process_next()
    result=client.get('/documents/'+uploaded.json()['id'],headers=owner).json()
    assert result['verification_response']['outcome']=='fabricated'
    assert not result['job']['result']['assessment']['file_verification_eligible']
