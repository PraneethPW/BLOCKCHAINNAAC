"""Versioned type annotations, provenance and family-safe research exports.

Classification annotations never enter the authenticity decision engine.
"""
import csv
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import String, Text, select, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, Session
from main import Base, Account, current, reviewer, db, now, uid, read_upload, store_file, STORAGE
from document_classification import CATEGORIES, CLASSES, VERSION, taxonomy

router=APIRouter(prefix='/classification')
ROOT=Path(__file__).with_name('datasets')
MANIFEST=ROOT/'classification.json'
LABELS=['genuine','fabricated','manipulated','corrupted','neutral']

class ClassificationRecord(Base):
    __tablename__='veris_classification_records'
    __table_args__=(UniqueConstraint('sha256',name='veris_classification_unique_file'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    sha256:Mapped[str]=mapped_column(String(64),index=True)
    filename:Mapped[str]=mapped_column(String(255))
    storage_name:Mapped[str]=mapped_column(String(100))
    annotation:Mapped[str]=mapped_column(Text)
    reviewer_id:Mapped[str]=mapped_column(String(36))
    created_at:Mapped[str]=mapped_column(String(40),default=now)

def seed_records():
    rows=json.loads(MANIFEST.read_text(encoding='utf-8'))['records'] if MANIFEST.is_file() else []
    validated(rows)
    for row in rows:
        path=ROOT/row['filename']
        row['integrity']='intact' if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'] else 'unavailable'
    return rows

def split_for(family_id):
    bucket=int(hashlib.sha256(('veris-split-v1:'+family_id).encode()).hexdigest()[:8],16)%10
    return 'train' if bucket<7 else 'validation' if bucket<9 else 'test'

def family_for(issuer):
    canonical=re.sub(r'\W+',' ',issuer.casefold()).strip()
    return 'issuer:'+hashlib.sha256(canonical.encode()).hexdigest()[:24]

def validated(rows):
    """Reject split leakage and inconsistent immutable seed annotations."""
    hashes={};families={}
    for row in rows:
        if row['document_class'] not in CLASSES:raise ValueError('Unknown document class')
        if row['authenticity_label'] not in LABELS:raise ValueError('Unknown authenticity label')
        if row['category']!=CLASSES[row['document_class']]['category']:raise ValueError('Category/type mismatch')
        if not row.get('family_id') or not row.get('label_evidence'):raise ValueError('Missing provenance')
        if row['split']!=split_for(row['family_id']):raise ValueError('Invalid family split')
        previous=hashes.setdefault(row['sha256'],(row['document_class'],row['family_id']))
        if previous!=(row['document_class'],row['family_id']):raise ValueError('Conflicting hash annotations')
        if families.setdefault(row['family_id'],row['split'])!=row['split']:raise ValueError('Family leakage')
    return rows

def visible_records(u,s):
    rows=seed_records()
    if u.role=='reviewer':
        for record in s.scalars(select(ClassificationRecord).order_by(ClassificationRecord.created_at)):
            row=json.loads(record.annotation)
            # Expose integrity state without exporting private file contents.
            file=STORAGE/record.storage_name
            row['integrity']='intact' if file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==record.sha256 else 'unavailable'
            rows.append(row)
    return rows

def matched_type(data):
    digest=hashlib.sha256(data).hexdigest()
    for row in seed_records():
        if row['sha256']==digest:
            file=ROOT/row['filename']
            if file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==digest:return row
    return None

@router.get('/catalogue')
def catalogue(u:Account=Depends(current),s:Session=Depends(db)):
    rows=visible_records(u,s)
    coverage=[]
    for category in CATEGORIES+['Cross-category']:
        classes=[]
        for item in taxonomy():
            if item['category']!=category:continue
            records=[r for r in rows if r['document_class']==item['id'] and r.get('integrity','intact')=='intact']
            real=[r for r in records if r['origin']=='public_original']
            classes.append(dict(**item,documents=len(records),public_originals=len(real),
                                controlled=len(records)-len(real),families=len({r['family_id'] for r in records}),
                                labels={label:sum(r['authenticity_label']==label for r in records) for label in LABELS}))
        coverage.append(dict(category=category,classes=classes))
    return dict(version='1.0',classifier_version=VERSION,method='Explainable content rules with exact curated type references',
                trained_model=False,registration_allowed=u.role=='reviewer',records=rows,coverage=coverage,
                evaluation=dict(status='starter_corpus',accuracy=None,description='This small reference corpus is not a trained or independently validated fraud model. Empty classes need real documents. Split assignments reserve source families for future evaluation; no held-out accuracy is claimed.'),
                labels=LABELS,taxonomy=taxonomy())

@router.get('/export')
def export(format:str='json',u:Account=Depends(current),s:Session=Depends(db)):
    rows=visible_records(u,s)
    if format not in ['json','csv']:raise HTTPException(400,'Choose json or csv.')
    if format=='json':
        body=json.dumps(dict(schema_version='1.0',split_policy='SHA-256 source-family assignment, 70/20/10 buckets; no training performed',records=rows),ensure_ascii=False,indent=2)
        media='application/json'
    else:
        fields=['id','filename','sha256','category','document_class','authenticity_label','origin','issuer','period','source_url','retrieved_at','family_id','parent_id','alteration','split','label_evidence','integrity']
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        # Prevent spreadsheet formula execution in reviewer-entered annotations.
        for row in rows:
            safe={k:("'"+str(v) if str(v).lstrip().startswith(('=','+','-','@')) else v) for k,v in row.items()}
            writer.writerow(safe)
        body=stream.getvalue();media='text/csv'
    return Response(body,media_type=media,headers={'Content-Disposition':f'attachment; filename="Veris_Classification_Dataset.{format}"'})

@router.get('/files/{id}')
def file(id:str,u:Account=Depends(current),s:Session=Depends(db)):
    row=next((r for r in seed_records() if r['id']==id),None)
    if row:path=ROOT/row['filename']
    else:
        if u.role!='reviewer':raise HTTPException(404,'Reference not found.')
        record=s.get(ClassificationRecord,id)
        if not record:raise HTTPException(404,'Reference not found.')
        row=json.loads(record.annotation);path=STORAGE/record.storage_name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
        raise HTTPException(409,'Reference integrity check failed.')
    return Response(path.read_bytes(),media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="{id}{path.suffix}"'})

@router.post('/records',status_code=201)
async def register(file:UploadFile=File(...),document_class:str=Form(...),authenticity_label:str=Form(...),
                   issuer:str=Form(...),period:str=Form(...),label_evidence:str=Form(...),source_url:str=Form(''),
                   parent_id:str=Form(''),alteration:str=Form(''),u:Account=Depends(reviewer),s:Session=Depends(db)):
    if document_class not in CLASSES or authenticity_label not in LABELS:raise HTTPException(400,'Select valid class and label.')
    if not 3<=len(issuer.strip())<=200 or not 1<=len(period.strip())<=80 or not 30<=len(label_evidence.strip())<=5000:
        raise HTTPException(400,'Provide issuer, period and independent label evidence (at least 30 characters).')
    if len(source_url)>2000 or (source_url and (urlparse(source_url).scheme!='https' or not urlparse(source_url).hostname or urlparse(source_url).username)):
        raise HTTPException(400,'Source must be an HTTPS URL without credentials.')
    if len(alteration)>2000:raise HTTPException(400,'Alteration description is too long.')
    rows=visible_records(u,s)
    parent=next((r for r in rows if r['id']==parent_id),None) if parent_id else None
    if parent_id and not parent:raise HTTPException(400,'Select an existing source reference.')
    if parent and (parent['document_class']!=document_class or parent.get('integrity')!='intact'):raise HTTPException(400,'A derived version must retain its intact parent document type.')
    if authenticity_label=='manipulated' and (not parent or len(alteration.strip())<20):
        raise HTTPException(400,'A manipulated sample requires its parent reference and a specific alteration description.')
    data,name,ext=await read_upload(file);digest=hashlib.sha256(data).hexdigest()
    if any(r['sha256']==digest for r in rows):raise HTTPException(409,'This exact file already has a type annotation. Reuse its existing record.')
    from verification import inspect_bytes, FileInspectionError
    from authenticity import declaration_checks
    from starlette.concurrency import run_in_threadpool
    try:
        content,metadata,observations=await run_in_threadpool(inspect_bytes,data,ext)
        observations+=declaration_checks(content,metadata)
        if authenticity_label=='genuine' and any(c.get('blocking') and c['state']=='warn' for c in observations):
            raise HTTPException(409,'Blocking sample or integrity evidence conflicts with a genuine label.')
        if authenticity_label=='corrupted':raise HTTPException(409,'The file parsed successfully; corruption was not established.')
    except FileInspectionError as exc:
        if exc.category!='corrupted' or authenticity_label!='corrupted':raise HTTPException(400,str(exc)) from exc
    # Group all records from an issuer together; parents always inherit family.
    # This conservatively keeps templates, originals and derivatives out of other splits.
    family=parent['family_id'] if parent else family_for(issuer)
    id=uid();storage=store_file(data,ext)
    row=dict(id=id,filename=name,sha256=digest,category=CLASSES[document_class]['category'],document_class=document_class,
             authenticity_label=authenticity_label,origin='controlled_derivative' if parent else 'reviewer_reference',
             issuer=issuer.strip(),period=period.strip(),source_url=source_url,retrieved_at=now(),family_id=family,
             parent_id=parent_id or None,alteration=alteration.strip(),split=split_for(family),label_evidence=label_evidence.strip(),integrity='intact')
    try:
        s.add(ClassificationRecord(id=id,sha256=digest,filename=name,storage_name=storage,annotation=json.dumps(row),reviewer_id=u.id));s.commit()
    except IntegrityError:
        s.rollback();(STORAGE/storage).unlink(missing_ok=True)
        raise HTTPException(409,'This exact file already has a type annotation.')
    except Exception:s.rollback();(STORAGE/storage).unlink(missing_ok=True);raise
    return row

