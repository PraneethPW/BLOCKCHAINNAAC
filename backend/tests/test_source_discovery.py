import asyncio
import httpx
from authenticity import claims, publication_checks, assessment
from source_discovery import search_title


def test_metadata_title_search_removes_only_demonstration_suffix():
    claim=claims('First page heading',{'pdf_metadata':{'Title':'Learning from graphs with graph neural networks - educational review sample'}})
    assert claim['query_title']=='Learning from graphs with graph neural networks'
    assert claim['title'].endswith('educational review sample')
    assert claims('Learning from graphs with\ngraph neural networks\nAbstract\nA review',{})['query_title']==claim['query_title']


def test_crossref_exact_and_related_candidates_never_authenticate_uploaded_file():
    def response(request):
        assert request.url.host=='api.crossref.org'
        assert request.url.params['query.bibliographic']=='Learning from graphs'
        assert 'query.title' not in request.url.params
        return httpx.Response(200,json={'message':{'total-results':2,'items':[
            {'DOI':'10.1234/exact','title':['Learning from graphs'],'author':[{'given':'Test','family':'Author'}],'issued':{'date-parts':[[2026]]}},
            {'DOI':'10.1234/related','title':['Different graph paper']}]}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
            return await search_title(client,'Crossref','Learning from graphs')
    attempt,records=asyncio.run(run())
    assert attempt['state']=='complete' and attempt['returned_count']==2 and attempt['exact_title_count']==1
    assert [r['title_match'] for r in records]==['exact','related']
    assert all(r['scope']=='title_search_candidate' for r in records)
    checks=publication_checks(claims('Learning from graphs',{}),records,'Research publications')
    assert not assessment(checks)['verification_eligible']
    assert all(c['state']=='unknown' for c in checks)


def test_zero_results_and_service_failure_are_distinct_and_have_no_fake_candidates():
    for code,payload,state in [(200,{'resultList':{'result':[]},'hitCount':0},'complete'),(429,{},'unavailable'),(200,{'unsupported':True},'unavailable')]:
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(code,json=payload))) as client:
                return await search_title(client,'Europe PMC','A real query title')
        attempt,records=asyncio.run(run())
        assert attempt['state']==state and attempt['returned_count']==0 and records==[]
        assert attempt['checked_at']>=attempt['started_at'] and attempt['url'].startswith('https://www.ebi.ac.uk/')


def test_provider_results_are_durable_before_analysis_completes_and_history_is_real(client,monkeypatch):
    import main,verification
    from sqlalchemy import select
    from test_workflow import account
    owner=account(client)
    reviewer=account(client,'history-reviewer@example.com','reviewer')
    d=client.post('/documents?background=true',headers=owner,data={'category':'Research publications','period':'2026'},files={'file':('actual-test-input.txt',b'Learning from graphs\nAbstract\nResearch evidence requiring review','text/plain')}).json()
    async def title_search(title,on_result):
        assert title=='Learning from graphs'
        for provider,count in [('Crossref',1),('Europe PMC',0)]:
            record=dict(provider=provider,identifier='10.1234/lead',url='https://doi.org/10.1234/lead',checked_at=main.now(),state='found',title='A different title',authors=[],scope='title_search_candidate',query_title=title,title_match='related',detail='Related record only.')
            attempt=dict(provider=provider,mode='title',query=title,url='https://api.crossref.org/works' if provider=='Crossref' else 'https://www.ebi.ac.uk/europepmc/webservices/rest/search',checked_at=main.now(),state='complete',returned_count=count,exact_title_count=0,detail='Test provider response')
            on_result(attempt,[record] if count else [])
            with main.SessionLocal() as session:
                job=session.scalar(select(main.VerificationJob).where(main.VerificationJob.document_id==d['id']).order_by(main.VerificationJob.created_at.desc()))
                persisted=main.job_json(job)
                assert persisted['state']=='running'
                assert persisted['result']['searches'][-1]['provider']==provider
                assert persisted['timeline'][-1]['stage'].startswith(provider)
        return [],[]  # Callback owns the durable responses; no fabricated fallback.
    monkeypatch.setattr(verification,'discover_title',title_search)
    verification.process_next()
    result=client.get('/documents/'+d['id'],headers=owner).json()
    assert result['job']['state']=='complete' and len(result['job']['result']['searches'])==2
    assert result['status']=='unverified' and result['decisions']==[]
    assert any(e['kind']=='upload' for e in result['activity'])
    assert not any(e['kind']=='decision' for e in result['activity'])
    assert client.post('/documents/'+d['id']+'/verify',headers=owner).status_code==202
    verification.process_next()
    result=client.get('/documents/'+d['id'],headers=owner).json()
    assert sum(e['title']=='Verification queued' for e in result['activity'])==2
    decision=client.post('/documents/'+d['id']+'/decisions',headers=reviewer,json={'outcome':'flagged','reason':'Request an independently obtained issuer original for this document.','evidence':'No issuer original has been supplied.'})
    assert decision.status_code==200
    result=client.get('/documents/'+d['id'],headers=owner).json()
    human=[e for e in result['activity'] if e['kind']=='decision']
    assert len(human)==1 and human[0]['id']==result['decisions'][0]['id']
    assert human[0]['at']==result['decisions'][0]['created_at'] and human[0]['actor']==result['decisions'][0]['reviewer']
    report=client.get('/documents/'+d['id']+'/report',headers=owner)
    assert report.status_code==200 and report.content.startswith(b'%PDF-')
