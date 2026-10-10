"""Fetch original PDFs from explicitly supported publishers, never uploaded URLs."""
import asyncio
import hashlib
import io
import re
from urllib.parse import urljoin,urlsplit
import httpx
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from authenticity import ordered_dois
from datetime import datetime,timezone

MAX_BYTES=10*1024*1024
HOSTS={'www.nature.com','idp.nature.com','media.springernature.com'}

def allowed(url):
    parsed=urlsplit(url)
    return parsed.scheme=='https' and parsed.hostname in HOSTS and parsed.port in [None,443] and not parsed.username and not parsed.password

async def download_original(client,url):
    # The DOI generates the initial path. Every redirect is checked before requesting.
    for _ in range(6):
        if not allowed(url):raise ValueError('Publisher redirect left the supported HTTPS hosts.')
        async with client.stream('GET',url) as response:
            if response.status_code in [301,302,303,307,308]:
                url=urljoin(url,response.headers.get('location',''))
                continue
            response.raise_for_status()
            chunks=[];size=0
            async for chunk in response.aiter_bytes():
                size+=len(chunk)
                if size>MAX_BYTES:raise ValueError('Publisher PDF exceeds the 10 MB comparison limit.')
                chunks.append(chunk)
            data=b''.join(chunks)
            if not data.startswith(b'%PDF-'):raise ValueError('Publisher response was not a PDF original.')
            return data,url
    raise ValueError('Publisher redirect limit reached.')

async def compare_publisher_original(data,metadata,category):
    result=dict(state='not_applicable',provider='Nature / Springer Nature',url='',doi='',checked_at='',
                publisher_sha256='',uploaded_sha256=hashlib.sha256(data).hexdigest(),bytes=0,
                detail='Direct publisher byte comparison supports PDF research articles with a single front-page Nature DOI. Other documents use registered issuer evidence.')
    dois=metadata['claims']['primary_dois']
    if category!='Research publications' or metadata['format']!='pdf' or len(dois)!=1:return result
    match=re.fullmatch(r'10\.1038/(s\d{5}-\d{2,4}-\d{3,7}-[a-z0-9]{1,3})',dois[0])
    if not match:return result
    result.update(state='unavailable',doi=dois[0],url='https://www.nature.com/articles/'+match.group(1)+'.pdf')
    try:
        async with httpx.AsyncClient(timeout=12,follow_redirects=False,headers={'User-Agent':'Mozilla/5.0 (Veris original-file comparison)'}) as client:
            original,final_url=await asyncio.wait_for(download_original(client,result['url']),timeout=25)
        pdf=PdfReader(io.BytesIO(original),strict=True)
        if pdf.is_encrypted or not 1<=len(pdf.pages)<=100:raise ValueError('Publisher original exceeds inspection limits.')
        front=(pdf.pages[0].extract_text() or '')[:4500]
        if result['doi'] not in ordered_dois(front):raise ValueError('Publisher PDF front-page DOI did not match the requested article.')
        digest=hashlib.sha256(original).hexdigest()
        same=digest==result['uploaded_sha256']
        result.update(state='matched' if same else 'different',url=final_url,publisher_sha256=digest,bytes=len(original),
                      detail='Every uploaded byte matches the PDF retrieved directly from the publisher. This authenticates this published file, not institutional authorship or accreditation claims.' if same else
                      'The uploaded bytes differ from the publisher PDF. It may be an altered copy, an author manuscript or a re-export; difference alone does not establish deliberate fabrication.')
    except (httpx.HTTPError,ValueError,asyncio.TimeoutError,KeyError,TypeError,IndexError,PdfReadError):
        result['detail']='The official publisher original was unavailable or did not pass the bounded PDF inspection. No genuine or fake verdict was inferred from the download failure.'
    finally:result['checked_at']=datetime.now(timezone.utc).isoformat()
    return result
