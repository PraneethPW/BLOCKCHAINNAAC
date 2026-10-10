"""Durable verification passes. Public metadata is evidence, never a fraud verdict."""
import asyncio
import hashlib
import io
import json
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote
import httpx
from pypdf import PdfReader
from sqlalchemy import select, text

def timestamp():return datetime.now(timezone.utc).isoformat()
def normalize(value):return re.sub(r'\W+',' ',unicodedata.normalize('NFKC',value).lower()).strip()
def extract_dois(content):
    return sorted(set(x.rstrip('.,;:)]}').lower() for x in re.findall(r'\b10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+',content)))[:8]

def inspect_bytes(data,ext):
    from main import extract
    metadata={'bytes':len(data),'format':ext.lstrip('.'),'extraction':'native text','pages':None,'signature_fields':0,'ocr_pages':0}
    observations=[]
    content=extract(data,ext)
    if ext=='.pdf':
        pdf=PdfReader(io.BytesIO(data));metadata['pages']=len(pdf.pages)
        metadata['pdf_metadata']={str(k).lstrip('/'):str(v)[:500] for k,v in (pdf.metadata or {}).items() if str(k) in ['/CreationDate','/ModDate','/Producer','/Creator','/Author','/Title']}
        fields=pdf.get_fields() or {}
        metadata['signature_fields']=sum(1 for v in fields.values() if v.get('/FT')=='/Sig')
        if metadata['signature_fields']:observations.append({'name':'PDF signature fields','state':'unknown','detail':f"Detected {metadata['signature_fields']} signature fields. Certificate trust, revocation and signer identity require issuer validation; field presence is not authentication."})
        active=[]
        root=pdf.trailer['/Root']
        for key in ['/OpenAction','/AA']:
            if key in root:active.append(key)
        if '/Names' in root and '/JavaScript' in root['/Names']:active.append('JavaScript')
        if active:observations.append({'name':'PDF active content','state':'warn','detail':'Active document actions detected: '+', '.join(active)+'. Original is served as a download; inspect in a protected viewer.'})
        if len(content.strip())<100:
            import pymupdf
            import pytesseract
            from PIL import Image
            pieces=[]
            with pymupdf.open(stream=data,filetype='pdf') as rendered:
                # Bound CPU, image memory and OCR work. Long scanned files expose this limit.
                for page in list(rendered)[:12]:
                    if max(page.rect.width,page.rect.height)>2000:continue
                    native=page.get_text()
                    if len(native.strip())>=50:pieces.append(native);continue
                    pix=page.get_pixmap(dpi=130,alpha=False)
                    if pix.width*pix.height>8_000_000:continue
                    try:
                        pieces.append(pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes('png'))),timeout=12));metadata['ocr_pages']+=1
                    except (pytesseract.TesseractNotFoundError,RuntimeError):break
            if pieces:content='\n'.join(pieces)[:50000]
            metadata['extraction']='OCR + native text' if metadata['ocr_pages'] else 'No readable text / OCR unavailable'
            if len(pdf.pages)>12:observations.append({'name':'OCR coverage','state':'unknown','detail':'OCR is bounded to the first 12 pages. Additional scanned pages require a separate submission.'})
    elif ext in ['.png','.jpg','.jpeg']:metadata['extraction']='Tesseract OCR' if content.strip() else 'OCR unavailable / no readable text'
    # A normalization digest detects repeated text in files with different binary hashes.
    metadata['normalized_text_sha256']=hashlib.sha256(normalize(content).encode()).hexdigest() if content.strip() else ''
    metadata['dois']=extract_dois(content)
    return content,metadata,observations

async def public_record(client,provider,doi,document_text):
    encoded=quote(doi,safe='')
    endpoints={'Crossref':f'https://api.crossref.org/works/{encoded}','DataCite':f'https://api.datacite.org/dois/{encoded}','Europe PMC':'https://www.ebi.ac.uk/europepmc/webservices/rest/search'}
    url=endpoints[provider];params={'query':f'DOI:"{doi}"','format':'json','pageSize':1,'resultType':'core'} if provider=='Europe PMC' else None
    result={'provider':provider,'identifier':doi,'url':url if not params else url+'?query='+quote(params['query'])+'&format=json','checked_at':timestamp(),'state':'unavailable','detail':'','title':'','authors':[]}
    try:
        response=await client.get(url,params=params,headers={'User-Agent':'Veris-Evidence/2.0 (public scholarly metadata verification)'})
        if response.status_code==404:result.update(state='not_found',detail='No publicly available record in this registry. This is not proof of fraud.');return result
        if response.status_code!=200:result['detail']=f'Provider returned HTTP {response.status_code}; retry later.';return result
        payload=response.json()
        if provider=='Crossref':
            record=payload['message'];title=(record.get('title') or [''])[0];authors=[' '.join([a.get('given',''),a.get('family','')]).strip() for a in record.get('author',[])];returned_doi=record.get('DOI','');publisher=record.get('publisher','');year=(record.get('issued',{}).get('date-parts') or [[]])[0];year=year[0] if year else None
            updates=[x for x in record.get('update-to',[]) if x.get('type') in ['retraction','withdrawal']]
            if updates:result['notice']='Registry reports a retraction/withdrawal relation; inspect its context.'
        elif provider=='DataCite':
            record=payload['data']['attributes'];title=(record.get('titles') or [{}])[0].get('title','');authors=[a.get('name','') for a in record.get('creators',[])];returned_doi=record.get('doi','');publisher=record.get('publisher','');publisher=publisher.get('name','') if isinstance(publisher,dict) else publisher;year=record.get('publicationYear')
        else:
            records=payload.get('resultList',{}).get('result',[])
            if not records:result.update(state='not_found',detail='Not indexed by Europe PMC. Its coverage is subject-specific; absence is not proof of fraud.');return result
            record=records[0];title=record.get('title','');authors=[a.get('fullName','') for a in record.get('authorList',{}).get('author',[])];returned_doi=record.get('doi','');publisher=record.get('journalInfo',{}).get('journal',{}).get('title','');year=record.get('pubYear')
            if record.get('isRetracted')=='Y':result['notice']='Europe PMC marks this publication retracted; investigate the context.'
        if returned_doi.lower()!=doi.lower():result['detail']='Provider identifier did not match the requested DOI.';return result
        matched=bool(title and normalize(title) in normalize(document_text))
        result.update(state='found',title=title[:1000],authors=authors[:30],publisher=str(publisher)[:500],year=year,title_in_document=matched,detail='DOI metadata retrieved directly from the registry. '+('The registry title is present in the uploaded text.' if matched else 'Compare the registry title, authors and claimed affiliation against the submitted evidence.'))
    except (httpx.HTTPError,ValueError,KeyError,IndexError,TypeError):result['detail']='The public registry could not be reached or returned an unsupported response. No finding was inferred.'
    return result

async def corroborate(dois,content):
    async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
        # Only fixed registry hosts; uploaded URLs are never fetched.
        results=[]
        for doi in dois:
            results.extend(await asyncio.gather(*(public_record(client,p,doi,content) for p in ['Crossref','DataCite','Europe PMC'])))
        return results

def process_next():
    from main import SessionLocal,engine,VerificationJob,Document,Decision,STORAGE,run_checks,canonical,Archive
    with engine.connect() as lock:
        if engine.dialect.name=='postgresql' and not lock.scalar(text('SELECT pg_try_advisory_lock(82917625)')):return
        try:
            with SessionLocal() as s:
                stale=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
                job=s.scalar(select(VerificationJob).where((VerificationJob.state=='queued')|((VerificationJob.state=='running')&(VerificationJob.updated_at<stale))).order_by(VerificationJob.created_at).with_for_update())
                if not job:return
                doc=s.get(Document,job.document_id)
                if not doc or s.get(Archive,doc.id):job.state='failed';job.error='Document is unavailable.';s.commit();return
                def stage(label,progress):
                    job.state='running';job.stage=label;job.progress=progress;job.updated_at=timestamp();job.timeline=canonical([*json.loads(job.timeline),{'stage':label,'at':job.updated_at}]);s.commit()
                try:
                    stage('Inspecting original file integrity',10)
                    file=STORAGE/doc.storage_name;data=file.read_bytes()
                    if hashlib.sha256(data).hexdigest()!=doc.sha256:raise RuntimeError('Stored file fingerprint differs from the submission. Integrity investigation required.')
                    stage('Extracting text and examining file structure',25)
                    content,metadata,observations=inspect_bytes(data,file.suffix)
                    stage('Corroborating identifiers with public registries',55)
                    results=asyncio.run(corroborate(metadata['dois'],content)) if metadata['dois'] else []
                    stage('Comparing evidence and institutional context',85)
                    s.refresh(doc,with_for_update=True);doc.text=content;run_checks(doc,s)
                    checks=json.loads(doc.checks)+observations
                    # Same normalized extracted text under different bytes is an investigative lead.
                    if metadata['normalized_text_sha256']:
                        for other in s.scalars(select(Document).where(Document.id!=doc.id,Document.college==doc.college,Document.category==doc.category,Document.period==doc.period,~Document.id.in_(select(Archive.id)))):
                            if other.text.strip() and other.sha256!=doc.sha256 and normalize(other.text)==normalize(content):
                                checks.append({'name':'Repeated document text','state':'warn','detail':'A different file in the same institutional context contains identical normalized text. Inspect the version history.'});break
                    if results:
                        found=sum(r['state']=='found' for r in results);warnings=sum(bool(r.get('notice')) for r in results)
                        checks.append({'name':'Public publication registries','state':'warn' if warnings else 'pass' if found else 'unknown','detail':f'{len(metadata["dois"])} DOI identifiers queried across Crossref, DataCite and Europe PMC; {found} registry records found. Metadata presence does not prove institutional authorship or document authenticity.'})
                    else:checks.append({'name':'Public publication registries','state':'unknown','detail':'No DOI was extracted. Public metadata checks are unavailable for this document; obtain authorized issuer evidence.'})
                    doc.checks=canonical(checks)
                    if not s.scalar(select(Decision).where(Decision.document_id==doc.id)) and any(c['state']=='warn' for c in checks):doc.status='flagged'
                    job.result=canonical({'metadata':metadata,'sources':results,'checks':checks,'checked_at':timestamp(),'limitations':['Public registries do not establish institutional authorship.','Certificate trust and private issuer records require authorized access.']})
                    job.state='complete';job.stage='Ready for evidence review';job.progress=100;job.error='';job.updated_at=timestamp();job.timeline=canonical([*json.loads(job.timeline),{'stage':job.stage,'at':job.updated_at}]);s.commit()
                except Exception as exc:
                    s.rollback();job=s.get(VerificationJob,job.id);job.state='failed';job.stage='Verification needs attention';job.error=str(exc) if isinstance(exc,RuntimeError) else 'Document processing failed. Check the file format and retry. Your original evidence is retained.';job.updated_at=timestamp();s.commit()
        finally:
            if engine.dialect.name=='postgresql':lock.execute(text('SELECT pg_advisory_unlock(82917625)'))
