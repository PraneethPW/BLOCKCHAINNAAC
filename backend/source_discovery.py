"""Bounded public title searches. Candidate papers never authenticate submitted bytes."""
import asyncio
import time
from datetime import datetime, timezone
from urllib.parse import quote
import httpx
from authenticity import normal


def now():return datetime.now(timezone.utc).isoformat()


async def search_title(client, provider, title):
    started = now(); clock = time.monotonic()
    if provider == 'Crossref':
        url = 'https://api.crossref.org/works'
        params = {'query.bibliographic': title, 'rows': 3}
    else:
        url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
        # Escape syntax through a restricted, normalized title, not an uploaded URL.
        params = {'query': 'TITLE:"'+normal(title)+'"', 'format': 'json', 'pageSize': 3, 'resultType': 'core'}
    attempt = dict(provider=provider, mode='title', query=title, url=str(httpx.URL(url, params=params)),
                   started_at=started, checked_at=started, state='unavailable', returned_count=0,
                   exact_title_count=0, detail='', elapsed_ms=0)
    results = []
    try:
        response = await client.get(url, params=params, headers={'User-Agent': 'Veris-Evidence/3.1 (public scholarly metadata verification)'})
        if response.status_code != 200:
            attempt['detail'] = f'HTTP {response.status_code}. No conclusion was drawn; use Recheck to retry.'
        else:
            payload = response.json()
            records = payload['message']['items'] if provider == 'Crossref' else payload['resultList']['result']
            if not isinstance(records, list):raise ValueError('Unsupported registry response')
            attempt['total_reported'] = payload['message'].get('total-results') if provider == 'Crossref' else payload.get('hitCount')
            for record in records[:3]:
                if provider == 'Crossref':
                    heading = (record.get('title') or [''])[0]
                    authors = [' '.join([a.get('given',''), a.get('family','')]).strip() for a in record.get('author', [])]
                    doi = record.get('DOI', '')
                    publisher = record.get('publisher', '')
                    dates = (record.get('issued', {}).get('date-parts') or [[]])[0]
                    year = dates[0] if dates else None
                else:
                    heading = record.get('title', '')
                    authors = [a.get('fullName','') for a in record.get('authorList', {}).get('author', [])]
                    doi = record.get('doi', '')
                    publisher = record.get('journalInfo', {}).get('journal', {}).get('title', '')
                    year = record.get('pubYear')
                if not heading:continue
                exact = normal(heading) == normal(title)
                results.append(dict(provider=provider, identifier=doi, url='https://doi.org/'+quote(doi,safe='/') if doi else attempt['url'],
                                    checked_at=now(), state='found', title=str(heading)[:1000], authors=authors[:30],
                                    publisher=str(publisher)[:500], year=year, scope='title_search_candidate', query_title=title,
                                    title_match='exact' if exact else 'related', detail='Same normalized title; inspect authors, dates and issuer evidence.' if exact else 'Related search result. Its title differs from the submitted title; it does not corroborate this document.'))
            attempt.update(state='complete', returned_count=len(results), exact_title_count=sum(r['title_match']=='exact' for r in results),
                           detail='Live registry search completed. Related results are investigation leads.' if results else 'No records returned for this query. Registry coverage is limited; absence does not prove fraud.')
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        attempt['detail'] = 'Registry unavailable or response unsupported. No results were invented; use Recheck to retry.'
        results = []
    attempt.update(checked_at=now(), elapsed_ms=round((time.monotonic()-clock)*1000))
    return attempt, results


async def discover_title(title, on_result=None):
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        async def query(provider):
            attempt, records = await search_title(client, provider, title)
            if on_result:on_result(attempt, records)
            return attempt, records
        responses = await asyncio.gather(*(query(p) for p in ['Crossref', 'Europe PMC']))
    return [a for a,_ in responses], [r for _,records in responses for r in records]
