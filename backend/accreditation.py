"""Institutional claims and sealed evidence behind confirmed findings.

Criteria references are supplied by the institution; this is not an official
NAAC framework, grade calculator or substitute for issuer authority.
"""
import hashlib
import json
import re
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from authenticity import ENGINE_VERSION, normal, assessment
from main import (AccreditationClaim, ClaimReview, EvidenceSnapshot, Document,
                  Decision, SourceRecord, SourceMetric, VerificationJob, Anchor,
                  Archive, Account, STORAGE, canonical, now, uid, current,
                  reviewer, db, get_document, visible_documents, job_json)

router = APIRouter()


def stored_digest(name):
    path = (STORAGE/name).resolve()
    if not path.is_relative_to(STORAGE) or not path.is_file():return None
    try:return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:return None


def contextual_sources(doc, sources):
    return [r for r in sources if (r.college,r.category,r.period)==(doc.college,doc.category,doc.period)]


def compare_claim(claim, doc, sources, metrics, digest_cache, job=None):
    def intact(source):
        if source.storage_name not in digest_cache:digest_cache[source.storage_name]=stored_digest(source.storage_name)
        return digest_cache[source.storage_name]==source.sha256
    candidates=[r for r in contextual_sources(doc,sources) if normal(r.issuer)==normal(claim.issuer)]
    issuer=[r for r in candidates if intact(r)]
    source_ids=[r.id for r in issuer]
    result=dict(state='issuer_evidence_needed',eligible=False,detail='No intact registered evidence from the declared issuer for this institution, category and reporting period.',source_ids=source_ids,claimed_quantity=claim.quantity,document_quantities=[],issuer_quantities=[])
    if candidates and not issuer:result.update(state='source_integrity_conflict',detail='The registered issuer evidence is missing or has changed. Restore independent evidence before reviewing.')
    if issuer:
        result.update(state='review_required',detail='Issuer evidence is registered. An authorized reviewer must assess whether it supports this specific claim.')
        if claim.quantity is not None:
            values=set(int(x) for x in re.findall(r'(\d+)\s+(?:students?\s+)?(?:placed|placements)\b',doc.text,re.I))
            values.update(int(x) for x in re.findall(r'\b(?:placements|students placed)\s*[:=\-]\s*(\d+)',doc.text,re.I))
            counts={metrics[r.id] for r in issuer if r.id in metrics}
            result.update(document_quantities=sorted(values),issuer_quantities=sorted(counts))
            if len(values)==1 and len(counts)==1:
                agree=values==counts=={claim.quantity}
                result.update(state='counts_agree' if agree else 'claim_conflict',detail=f'Institution claims {claim.quantity}; document states {next(iter(values))}; declared issuer records {next(iter(counts))}. '+('Counts agree; they still require an authorized review.' if agree else 'These counts differ. Request clarification and independent evidence.'))
            else:result.update(state='count_evidence_incomplete',detail='A single readable document count and a single authorized issuer count are required. Missing or ambiguous counts cannot support acceptance.')
        exact=any(r.sha256==doc.sha256 for r in issuer)
        if doc.storage_name not in digest_cache:digest_cache[doc.storage_name]=stored_digest(doc.storage_name)
        current_job=bool(job and job.state=='complete' and json.loads(job.result).get('engine_version')==ENGINE_VERSION)
        result['eligible']=bool(current_job and exact and digest_cache[doc.storage_name]==doc.sha256 and doc.status=='verified' and assessment(json.loads(doc.checks))['verification_eligible'] and (claim.quantity is None or result['state']=='counts_agree'))
    if any(c.get('blocking') and c['state']=='warn' for c in json.loads(doc.checks)):
        result.update(eligible=False,document_conflict=True)
    return result


def review_json(review):
    return {k:getattr(review,k) for k in ['id','outcome','reason','evidence','reviewer','created_at']}


def claim_json(claim,doc,reviews,sources,metrics,cache,job):
    ordered=sorted(reviews,key=lambda r:r.created_at)
    return {**{k:getattr(claim,k) for k in ['id','document_id','criterion','statement','issuer','quantity','created_at']},
            'category':doc.category,'period':doc.period,'document_status':doc.status,
            'comparison':compare_claim(claim,doc,sources,metrics,cache,job),
            'status':ordered[-1].outcome if ordered else 'submitted',
            'reviews':[review_json(r) for r in ordered]}


class ClaimInput(BaseModel):
    document_id:str=Field(min_length=1,max_length=36)
    criterion:str=Field(min_length=2,max_length=80)
    statement:str=Field(min_length=20,max_length=2000)
    issuer:str=Field(min_length=2,max_length=200)
    quantity:int | None=Field(default=None,ge=0,le=1000000,strict=True)
    @field_validator('criterion','statement','issuer')
    @classmethod
    def trim(cls,value):
        value=value.strip()
        if len(value)<2:raise ValueError('Provide meaningful claim details.')
        return value


@router.post('/accreditation/claims',status_code=201)
def submit_claim(body:ClaimInput,u:Account=Depends(current),s:Session=Depends(db)):
    doc=get_document(s,body.document_id,u,True)
    if doc.owner_id!=u.id:raise HTTPException(403,'Only the submitting institution account can declare its claim.')
    if len(body.statement)<20:raise HTTPException(400,'Describe the institutional claim, not just the file name.')
    if body.quantity is not None and doc.category!='Student placements':raise HTTPException(400,'Structured quantity comparison currently supports Student placements only. Other claims require issuer evidence and review.')
    if s.scalar(select(AccreditationClaim).where(AccreditationClaim.document_id==doc.id,AccreditationClaim.criterion==body.criterion,AccreditationClaim.statement==body.statement,AccreditationClaim.issuer==body.issuer,AccreditationClaim.quantity==body.quantity)):
        raise HTTPException(409,'This exact claim is already submitted.')
    claim=AccreditationClaim(id=uid(),document_id=doc.id,owner_id=u.id,criterion=body.criterion,statement=body.statement,issuer=body.issuer,quantity=body.quantity)
    s.add(claim);s.commit()
    return {'id':claim.id,'created_at':claim.created_at}


class ClaimReviewInput(BaseModel):
    outcome:str
    reason:str=Field(min_length=20,max_length=5000)
    evidence:str=Field(min_length=10,max_length=5000)


@router.post('/accreditation/claims/{id}/reviews')
def review_claim(id:str,body:ClaimReviewInput,u:Account=Depends(reviewer),s:Session=Depends(db)):
    claim=s.scalar(select(AccreditationClaim).where(AccreditationClaim.id==id).with_for_update())
    if not claim:raise HTTPException(404,'Claim not found.')
    doc=get_document(s,claim.document_id,u,True)
    if body.outcome not in ['supported','clarification_required','insufficient_evidence']:raise HTTPException(400,'Choose a supported claim outcome.')
    if len(body.reason.strip())<20 or len(body.evidence.strip())<10:raise HTTPException(400,'Provide a substantive reason and evidence reference.')
    if body.outcome=='supported':
        sources=list(s.scalars(select(SourceRecord).where(~SourceRecord.id.in_(select(Archive.id)))))
        metrics={m.source_id:m.value for m in s.scalars(select(SourceMetric))}
        job=s.scalar(select(VerificationJob).where(VerificationJob.document_id==doc.id).order_by(VerificationJob.created_at.desc()))
        if not compare_claim(claim,doc,sources,metrics,{},job)['eligible']:
            raise HTTPException(409,'Support requires a verified original, intact evidence from the declared issuer, current completed checks and agreement on any structured quantity.')
    review=ClaimReview(claim_id=id,reviewer_id=u.id,reviewer=u.name,outcome=body.outcome,reason=body.reason.strip(),evidence=body.evidence.strip())
    s.add(review);s.commit();return review_json(review)


@router.get('/accreditation')
def dossiers(u:Account=Depends(current),s:Session=Depends(db)):
    docs=list(s.scalars(visible_documents(u).order_by(Document.created_at.desc())))
    by_id={d.id:d for d in docs};ids=list(by_id)
    claims=list(s.scalars(select(AccreditationClaim).where(AccreditationClaim.document_id.in_(ids)).order_by(AccreditationClaim.created_at))) if ids else []
    reviews=defaultdict(list)
    if claims:
        for r in s.scalars(select(ClaimReview).where(ClaimReview.claim_id.in_([c.id for c in claims]))):reviews[r.claim_id].append(r)
    sources=list(s.scalars(select(SourceRecord).where(~SourceRecord.id.in_(select(Archive.id))))) if claims else []
    metrics={m.source_id:m.value for m in s.scalars(select(SourceMetric))} if claims else {}
    anchors=list(s.scalars(select(Anchor).where(Anchor.case_id.in_(ids)))) if ids else []
    jobs={}
    if claims:
        for job in s.scalars(select(VerificationJob).where(VerificationJob.document_id.in_(ids)).order_by(VerificationJob.created_at.desc())):jobs.setdefault(job.document_id,job)
    grouped={};cache={}
    for d in docs:
        key=hashlib.sha256(canonical([d.owner_id,d.period]).encode()).hexdigest()[:24]
        group=grouped.setdefault(key,dict(id=key,institution=d.college,period=d.period,documents=[],claims=[],anchors=[]))
        group['documents'].append({k:getattr(d,k) for k in ['id','filename','category','sha256','status','created_at']})
        group['claims'].extend(claim_json(c,d,reviews[c.id],sources,metrics,cache,jobs.get(d.id)) for c in claims if c.document_id==d.id)
        group['anchors'].extend({k:getattr(a,k) for k in ['id','case_id','state','tx_hash','outcome']} for a in anchors if a.case_id==d.id)
    return dict(dossiers=list(grouped.values()),updated_at=now(),framework='Institution-declared criteria · independent accreditation prototype',institution_identity='Self-declared; official institutional onboarding is not connected',blockchain_scope='Confirmed document findings and linked appeals only')


def seal_decision(doc,decision,s):
    """Hash and persist the exact review-time evidence, not only a narrative."""
    claims=list(s.scalars(select(AccreditationClaim).where(AccreditationClaim.document_id==doc.id).order_by(AccreditationClaim.id)))
    sources=list(s.scalars(select(SourceRecord).where(SourceRecord.college==doc.college,SourceRecord.category==doc.category,SourceRecord.period==doc.period,~SourceRecord.id.in_(select(Archive.id))).order_by(SourceRecord.id)))
    job=s.scalar(select(VerificationJob).where(VerificationJob.document_id==doc.id).order_by(VerificationJob.created_at.desc()))
    payload=dict(schema='veris-accreditation-evidence/1',document={k:getattr(doc,k) for k in ['id','filename','college','category','period','sha256','created_at']},
                 original_digest_at_review=stored_digest(doc.storage_name),checks=json.loads(doc.checks),verification=job_json(job) if job else None,
                 decision={k:getattr(decision,k) for k in ['id','reviewer_id','reviewer','outcome','reason','evidence','created_at']},claims=[],issuer_records=[])
    for c in claims:
        payload['claims'].append({**{k:getattr(c,k) for k in ['id','criterion','statement','issuer','quantity','created_at']},'reviews':[review_json(r) for r in s.scalars(select(ClaimReview).where(ClaimReview.claim_id==c.id).order_by(ClaimReview.created_at))]})
    for source in sources:
        metric=s.scalar(select(SourceMetric).where(SourceMetric.source_id==source.id))
        payload['issuer_records'].append({**{k:getattr(source,k) for k in ['id','issuer','reference','reviewer_id','sha256','college','category','period']},'current_digest':stored_digest(source.storage_name),'placement_count':metric.value if metric else None})
    serialized=canonical(payload);digest=hashlib.sha256(serialized.encode()).hexdigest()
    s.add(EvidenceSnapshot(id=decision.id,document_id=doc.id,payload=serialized,digest=digest,created_at=decision.created_at))
    return digest


def receipt_bundle(anchor,doc,s):
    snapshot=s.get(EvidenceSnapshot,anchor.id)
    if snapshot:
        payload=snapshot.payload;scope='Full review-time evidence snapshot'
    else:
        decision=s.get(Decision,anchor.id)
        if not decision:raise HTTPException(409,'The original decision is unavailable; its evidence digest cannot be reconstructed.')
        payload=canonical({'decision_id':decision.id,'reason':decision.reason,'evidence':decision.evidence,'reviewer_id':decision.reviewer_id,'outcome':decision.outcome,'timestamp':decision.created_at})
        scope='Legacy decision narrative only; historical source results were not sealed'
    digest=hashlib.sha256(payload.encode()).hexdigest()
    source_integrity=[];context_matches=None;decision_matches=None;claims_match=None;summary=None
    if snapshot:
        try:
            manifest=json.loads(payload)
            valid=(manifest.get('schema')=='veris-accreditation-evidence/1' and
                   isinstance(manifest.get('document'),dict) and isinstance(manifest.get('decision'),dict) and
                   isinstance(manifest.get('claims'),list) and isinstance(manifest.get('issuer_records'),list))
        except (ValueError,AttributeError):valid=False
        if not valid:raise HTTPException(409,'Stored review evidence is unreadable or has an invalid schema. No audit match can be established; restore the original snapshot.')
        summary=dict(document=manifest['document'],claims=[{k:c.get(k) for k in ['criterion','statement','issuer','quantity']} for c in manifest['claims']],
                     decision={k:manifest['decision'].get(k) for k in ['reviewer','outcome','reason','evidence','created_at']},
                     issuer_records=[{k:r.get(k) for k in ['issuer','reference','placement_count']} for r in manifest['issuer_records']])
        context_matches=all(getattr(doc,k,None)==v for k,v in manifest['document'].items())
        decision=s.get(Decision,anchor.id)
        decision_matches=bool(decision and all(getattr(decision,k)==v for k,v in manifest['decision'].items()))
        claims_match=True
        for sealed_claim in manifest['claims']:
            claim=s.get(AccreditationClaim,sealed_claim['id'])
            if not claim or any(getattr(claim,k)!=v for k,v in sealed_claim.items() if k!='reviews'):claims_match=False
            for sealed_review in sealed_claim['reviews']:
                review=s.get(ClaimReview,sealed_review['id'])
                if not review or review_json(review)!=sealed_review:claims_match=False
        for evidence in manifest['issuer_records']:
            source=s.get(SourceRecord,evidence['id'])
            metric=s.scalar(select(SourceMetric).where(SourceMetric.source_id==evidence['id']))
            intact=bool(source and stored_digest(source.storage_name)==evidence['sha256'] and all(getattr(source,k)==evidence[k] for k in ['issuer','reference','reviewer_id','sha256','college','category','period']) and (metric.value if metric else None)==evidence['placement_count'])
            source_integrity.append(dict(id=evidence['id'],intact=intact))
    from ledger_proof import expected_record, network_config
    network,address,chain_id,rpc=network_config(s)
    return dict(schema='veris-audit-proof/1',record_id=anchor.id,document_id=doc.id,network=network,chain_id=chain_id,contract=address,
                transaction_hash=anchor.tx_hash,snapshot_scope=scope,canonical_payload=payload,snapshot_digest=digest,
                snapshot_matches_ledger_digest=digest==anchor.evidence_hash,original_matches_submitted_digest=stored_digest(doc.storage_name)==anchor.document_hash==doc.sha256,
                issuer_source_integrity=source_integrity,
                evidence_summary=summary,
                document_context_matches_snapshot=context_matches,current_decision_matches_snapshot=decision_matches,claim_context_matches_snapshot=claims_match,
                expected_record=expected_record(anchor),generated_at=now(),trust_model='Centrally operated development chain; independent consortium validators are not configured' if network=='private-devnet' else 'Ethereum Sepolia test network')


def permitted_anchor(id,u,s):
    anchor=s.get(Anchor,id)
    if not anchor:raise HTTPException(404,'Ledger record not found.')
    return anchor,get_document(s,anchor.case_id,u)


@router.get('/ledger/{id}/proof')
def check_proof(id:str,u:Account=Depends(current),s:Session=Depends(db)):
    anchor,doc=permitted_anchor(id,u,s)
    bundle=receipt_bundle(anchor,doc,s)
    from ledger_proof import check_chain, network_config, payload_binding
    _,_,_,rpc=network_config(s)
    chain=check_chain(bundle,rpc)
    bound=payload_binding(bundle)
    bundle.pop('canonical_payload')
    return {**bundle,'chain_check':chain,'snapshot_binding_matches':bound,'verified':bound and bundle['snapshot_matches_ledger_digest'] and bundle['original_matches_submitted_digest'] and all(r['intact'] for r in bundle['issuer_source_integrity']) and all(bundle[k] is not False for k in ['document_context_matches_snapshot','current_decision_matches_snapshot','claim_context_matches_snapshot']) and chain['state']=='match'}


@router.get('/ledger/{id}/proof-file')
def export_proof(id:str,u:Account=Depends(current),s:Session=Depends(db)):
    anchor,doc=permitted_anchor(id,u,s)
    bundle=receipt_bundle(anchor,doc,s)
    return Response(canonical(bundle),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="{id}-audit-proof.json"'})
