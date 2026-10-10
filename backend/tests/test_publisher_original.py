"""A registry match or forged download must never become file authentication."""
import asyncio,io
import httpx
from reportlab.pdfgen import canvas
from authenticity import assessment,finding,ENGINE_VERSION
import publisher_original as publisher
import verification
from test_workflow import account

DOI='10.1038/s41586-020-2649-2'
URL='https://www.nature.com/articles/s41586-020-2649-2.pdf'

def pdf_bytes(doi=DOI,content='Original publisher regression content'):
    buf=io.BytesIO();pdf=canvas.Canvas(buf)
    pdf.setTitle('Publisher regression report')
    pdf.drawString(40,780,'Publisher regression report')
    pdf.drawString(40,750,'DOI: '+doi)
    pdf.drawString(40,720,content)
    pdf.showPage();pdf.save();return buf.getvalue()

def install_transport(monkeypatch,handler):
    factory=httpx.AsyncClient
    monkeypatch.setattr(publisher.httpx,'AsyncClient',lambda **kw:factory(transport=httpx.MockTransport(handler),**kw))

def metadata(dois=None):return dict(format='pdf',claims={'primary_dois':[DOI] if dois is None else dois})

def test_download_redirect_to_private_or_unapproved_host_is_never_requested():
    requests=[]
    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            try:await publisher.download_original(client,URL)
            except ValueError:return
            assert False,'An unapproved redirect was accepted.'
    asyncio.run(run());assert requests==[URL]
    assert not publisher.allowed('https://www.nature.com.attacker.invalid/a.pdf')
    assert not publisher.allowed('https://user@www.nature.com/a.pdf')
    assert not publisher.allowed('https://www.nature.com:444/a.pdf')

def test_reference_identifiers_and_other_categories_do_not_trigger_publisher_queries(monkeypatch):
    def forbidden(**kwargs):raise AssertionError('No publisher request is allowed for an inapplicable document.')
    monkeypatch.setattr(publisher.httpx,'AsyncClient',forbidden)
    for info,category in [(metadata([]),'Research publications'),(metadata(),'Student placements'),(metadata([DOI,'10.1234/other']),'Research publications')]:
        assert asyncio.run(publisher.compare_publisher_original(b'document',info,category))['state']=='not_applicable'

def test_only_exact_bytes_with_correct_publisher_doi_can_authenticate(monkeypatch):
    official=pdf_bytes();install_transport(monkeypatch,lambda request:httpx.Response(200,content=official))
    match=asyncio.run(publisher.compare_publisher_original(official,metadata(),'Research publications'))
    assert match['state']=='matched' and match['publisher_sha256']==match['uploaded_sha256']
    alternate=pdf_bytes(content='Different author copy with the same DOI')
    different=asyncio.run(publisher.compare_publisher_original(alternate,metadata(),'Research publications'))
    assert different['state']=='different' and different['publisher_sha256']!=different['uploaded_sha256']

def test_unavailable_html_or_wrong_doi_publisher_pdf_never_authenticates(monkeypatch):
    data=pdf_bytes(doi='10.1038/s41586-020-9999-2')
    for response in [httpx.Response(503),httpx.Response(200,content=b'<html>Paywall</html>'),httpx.Response(200,content=data)]:
        install_transport(monkeypatch,lambda request:response)
        assert asyncio.run(publisher.compare_publisher_original(data,metadata(),'Research publications'))['state']=='unavailable'
        monkeypatch.undo()

def test_full_job_verifies_publisher_file_without_accepting_institutional_claim(client,monkeypatch):
    owner=account(client);official=pdf_bytes()
    install_transport(monkeypatch,lambda request:httpx.Response(200,content=official))
    async def no_records(*args):return []
    monkeypatch.setattr(verification,'corroborate',no_records)
    uploaded=client.post('/documents?background=true',headers=owner,data={'category':'Research publications','period':'2020'},files={'file':('arbitrary-filename.pdf',official,'application/pdf')})
    verification.process_next()
    result=client.get('/documents/'+uploaded.json()['id'],headers=owner).json()
    assert result['job']['state']=='complete' and result['job']['result']['engine_version']==ENGINE_VERSION
    assert result['verification_response']['code']=='publisher_match'
    assert result['verification_response']['outcome']=='genuine' and result['status']=='verified'
    assert result['job']['result']['publisher_original']['state']=='matched'
    assert result['job']['result']['assessment']['file_verification_eligible']
    assert not result['job']['result']['assessment']['verification_eligible']
    assert result['decisions']==[] and client.get('/ledger',headers=owner).json()==[]
    checks=[finding('Publisher original comparison','pass','An independently retrieved publisher byte match.')]
    assert assessment(checks)['file_verification_eligible'] and not assessment(checks)['verification_eligible']
