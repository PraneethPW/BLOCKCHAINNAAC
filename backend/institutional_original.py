"""Compare identifiable NIRF Overall reports with originals from the official host."""
import asyncio
import hashlib
import io
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import httpx
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_BYTES = 10 * 1024 * 1024
HOSTS = {'www.nirfindia.org', 'nirfindia.org'}


def identity(front):
    """Front-page identifiers select a query; they never establish authenticity."""
    if not all(re.search(pattern, front, re.I) for pattern in (
        r'National\s+Institutional\s+Ranking\s+Framework',
        r'Ministry\s+of\s+Education', r'Government\s+of\s+India',
    )):
        return None
    years = re.findall(r"Data\s+Submitted\s+by\s+Institution\s+for\s+India\s+Rankings\s*['’]?\s*(20\d{2})", front, re.I)
    institutes = re.findall(r'Institute\s+Name:\s*([^\[\n]+)\s*\[(IR-O-[UCI]-\d{4})\]', front)
    if len(years) != 1 or len(institutes) != 1 or not 2016 <= int(years[0]) <= datetime.now(timezone.utc).year:
        return None
    name, identifier = institutes[0]
    return dict(year=years[0], identifier=identifier, institution=' '.join(name.split()))


def allowed(url):
    try:
        parsed = urlsplit(url)
        return parsed.scheme == 'https' and parsed.hostname in HOSTS and parsed.port in (None, 443) and not parsed.username and not parsed.password
    except ValueError:
        return False


async def download_original(client, url):
    for _ in range(6):
        if not allowed(url):
            raise ValueError('Institutional redirect left supported HTTPS hosts.')
        async with client.stream('GET', url) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                url = urljoin(url, response.headers.get('location', ''))
                continue
            response.raise_for_status()
            chunks, size = [], 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError('Official PDF exceeds the comparison limit.')
                chunks.append(chunk)
            data = b''.join(chunks)
            if not data.startswith(b'%PDF-'):
                raise ValueError('Official response is not a PDF.')
            return data, url
    raise ValueError('Official PDF redirect limit reached.')


async def compare_institutional_original(data, metadata):
    result = dict(state='not_applicable', provider='NIRF / Ministry of Education', url='', identifier='', year='', institution='',
                  checked_at='', source_sha256='', uploaded_sha256=hashlib.sha256(data).hexdigest(), bytes=0,
                  detail='Direct institutional comparison supports identifiable official NIRF Overall PDF reports. Other records need an independent issuer original.')
    candidate = identity(metadata.get('front_page_text', '')) if metadata.get('format') == 'pdf' else None
    if not candidate:
        return result
    result.update(candidate, state='unavailable', url=f"https://www.nirfindia.org/nirfpdfcdn/{candidate['year']}/pdf/Overall/{candidate['identifier']}.pdf")
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=False, headers={'User-Agent': 'Veris official-original comparison'}) as client:
            original, final_url = await asyncio.wait_for(download_original(client, result['url']), timeout=25)
        pdf = PdfReader(io.BytesIO(original), strict=True)
        if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 100:
            raise ValueError('Official PDF exceeds inspection limits.')
        source = identity((pdf.pages[0].extract_text() or '')[:8000])
        if not source or any(source[key] != candidate[key] for key in ('year', 'identifier')):
            raise ValueError('Official PDF report identity differs from the requested identity.')
        digest = hashlib.sha256(original).hexdigest()
        same = digest == result['uploaded_sha256']
        result.update(source, state='matched' if same else 'different', url=final_url, source_sha256=digest, bytes=len(original),
                      detail=f"Every uploaded byte matches the {source['year']} NIRF report for {source['institution']} ({source['identifier']}) retrieved directly from the official website. This authenticates the report file; it does not validate its self-reported claims or another institution's ownership." if same else
                      'The uploaded file differs from the official NIRF report. It could be edited, an excerpt or a re-export. A byte difference alone does not establish fraud.')
    except (httpx.HTTPError, ValueError, asyncio.TimeoutError, KeyError, TypeError, IndexError, PdfReadError):
        result['detail'] = 'The official institutional PDF was unavailable or failed report identity or format inspection. This lookup did not establish authenticity; no fake classification was inferred from a source failure.'
    finally:
        result['checked_at'] = datetime.now(timezone.utc).isoformat()
    return result
