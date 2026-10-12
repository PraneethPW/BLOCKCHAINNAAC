"""Versioned exact-file labels with declared provenance, never inferred AI truth."""
import hashlib,json
from pathlib import Path
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from fastapi.responses import Response
from sqlalchemy import String,Text,select
from sqlalchemy.orm import Mapped,mapped_column,Session
from main import Base,Account,STORAGE,current,reviewer,db,now,uid,read_upload,store_file,CATEGORIES,Archive

ROOT=Path(__file__).with_name('datasets')
router=APIRouter()
class DatasetRecord(Base):
    __tablename__='veris_dataset_records'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    sha256:Mapped[str]=mapped_column(String(64),index=True)
    label:Mapped[str]=mapped_column(String(20))
    college:Mapped[str]=mapped_column(String(200))
    category:Mapped[str]=mapped_column(String(100))
    period:Mapped[str]=mapped_column(String(80))
    reference:Mapped[str]=mapped_column(Text)
    storage_name:Mapped[str]=mapped_column(String(100))
    reviewer_id:Mapped[str]=mapped_column(String(36))
    created_at:Mapped[str]=mapped_column(String(40),default=now)

def manifest():return json.loads((ROOT/'manifest.json').read_text())

def compare(doc,data,s):
    digest=hashlib.sha256(data).hexdigest();catalogue=manifest()
    result=dict(version=catalogue['version'],method=catalogue['method'],state='not_found',label=None,reference_id=None,scope=None,sha256=digest,source_url='',checked_at=now(),detail='No exact file fingerprint appears in the configured reference dataset. Absence does not prove fraud.')
    for record in catalogue['records']:
        if record['sha256']!=digest or record['category'] not in ['All categories',doc.category]:continue
        file=ROOT/record['filename']
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=record['sha256']:
            result.update(state='unavailable',detail='Dataset original failed its stored fingerprint check. No dataset label was applied.');return result
        result.update(state='matched',label=record['label'],reference_id=record['id'],scope=record['scope'],source_url=record['source_url'],detail=record['reference']+'. '+record['detail'])
        break
    records=list(s.scalars(select(DatasetRecord).where(DatasetRecord.sha256==digest,DatasetRecord.college==doc.college,DatasetRecord.category==doc.category,DatasetRecord.period==doc.period)))
    intact=[r for r in records if (STORAGE/r.storage_name).is_file() and hashlib.sha256((STORAGE/r.storage_name).read_bytes()).hexdigest()==r.sha256]
    labels={r.label for r in intact}
    if result['state']=='matched':labels.add(result['label'])
    if len(labels)>1:
        result.update(state='conflict',label=None,reference_id=None,scope=None,detail='Configured dataset and authorized context-specific references disagree on the label. No label was selected.')
        return result
    if result['state']=='matched':return result
    if records and not intact:result.update(state='unavailable',detail='Registered dataset evidence is missing or changed. No dataset label was applied.')
    elif intact:
        r=intact[-1];result.update(state='matched',label=r.label,reference_id=r.id,scope='reviewer_registered',detail='Exact byte match to an intact, context-matched reference labeled by an authorized reviewer. Evidence: '+r.reference)
    return result

@router.get('/dataset')
def catalogue(u:Account=Depends(current),s:Session=Depends(db)):
    value=manifest();records=value['records']
    registered=list(s.scalars(select(DatasetRecord).order_by(DatasetRecord.created_at.desc()))) if u.role=='reviewer' else []
    return dict(**value,counts={label:sum(r['label']==label for r in records) for label in ['genuine','fabricated','neutral']},registered=[{k:getattr(r,k) for k in ['id','sha256','label','college','category','period','reference','created_at']} for r in registered],registration_allowed=u.role=='reviewer',scope='Two official NIRF originals and twelve clearly labeled controlled fixtures. This is a reference dataset, not a trained fraud model.')

@router.get('/dataset/test-documents')
def test_documents(u:Account=Depends(current)):
    return Response((ROOT/'test-documents.zip').read_bytes(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="Veris_Reference_Dataset.zip"'})

@router.post('/dataset/records',status_code=201)
async def register(file:UploadFile=File(...),label:str=Form(...),college:str=Form(...),category:str=Form(...),period:str=Form(...),reference:str=Form(...),u:Account=Depends(reviewer),s:Session=Depends(db)):
    if label not in ['genuine','fabricated','neutral'] or category not in CATEGORIES or not 3<=len(college.strip())<=200 or not 1<=len(period.strip())<=80 or not 30<=len(reference.strip())<=5000:raise HTTPException(400,'Provide a supported label, institutional context and at least 30 characters of independently established evidence.')
    data,name,ext=await read_upload(file)
    from verification import inspect_bytes
    from starlette.concurrency import run_in_threadpool
    content,metadata,observations=await run_in_threadpool(inspect_bytes,data,ext)
    from authenticity import declaration_checks
    observations.extend(declaration_checks(content,metadata))
    if label=='genuine' and any(c.get('blocking') and c['state']=='warn' for c in observations):raise HTTPException(409,'A document with blocking integrity or sample findings cannot be registered as genuine.')
    digest=hashlib.sha256(data).hexdigest()
    if s.scalar(select(DatasetRecord).where(DatasetRecord.sha256==digest,DatasetRecord.college==college.strip(),DatasetRecord.category==category,DatasetRecord.period==period.strip(),DatasetRecord.label==label)):raise HTTPException(409,'This reference label and context are already registered.')
    storage=store_file(data,ext)
    try:
        r=DatasetRecord(sha256=digest,label=label,college=college.strip(),category=category,period=period.strip(),reference=reference.strip(),storage_name=storage,reviewer_id=u.id)
        s.add(r);s.commit();return dict(id=r.id,sha256=r.sha256,label=r.label,scope='reviewer_registered')
    except Exception:s.rollback();(STORAGE/storage).unlink(missing_ok=True);raise
