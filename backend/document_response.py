"""Plain-language results derived from recorded evidence, never guessed verdicts."""
from authenticity import ENGINE_VERSION


def verification_response(document):
    checks=document['checks'];job=document.get('job');decisions=document.get('decisions',[])
    latest=decisions[-1] if decisions else None
    blocking=[c for c in checks if c['state']=='warn' and c.get('blocking')]
    warnings=[c for c in checks if c['state']=='warn']
    issuer=next((c for c in checks if c['name']=='Authorized source comparison' and c['state']=='pass'),None)
    complete=bool(job and job['state']=='complete' and job['result'].get('engine_version')==ENGINE_VERSION)

    def result(code,title,reason,action,tone='warning',acceptance='not_verified'):
        return dict(code=code,title=title,reason=reason,action=action,tone=tone,acceptance=acceptance,
                    analysis_complete=complete,findings=[c['name'] for c in warnings])

    if job and job['state'] in ['queued','running']:
        return result('checking','Checking your document',job['stage'],'The result updates automatically when the checks finish.','running','processing')
    if document['status']=='confirmed_fraud' and latest and latest['outcome']=='confirmed_fraud':
        return result('fraud_confirmed','Fraud confirmed by authorized review',latest['reason'],'Read the recorded evidence and decision history. Any upheld appeal appends a linked correction.','danger','confirmed_fraud')
    integrity=next((c for c in blocking if c.get('kind')=='integrity' and
                    (c['name']!='Original file integrity and processing' or 'fingerprint differs' in c['detail'].lower())),None)
    if integrity:
        changed='fingerprint differs' in integrity['detail'].lower()
        return result('integrity_failed','Stored original has changed' if changed else 'File integrity check failed',integrity['detail'],'Obtain a fresh original from the issuer. This file cannot be accepted while its integrity check fails.','danger','blocked')
    if job and job['state']=='failed':
        return result('check_failed','Document checks could not be completed',job['error'],'Retry the checks or upload a readable original. No authenticity decision was inferred.','danger','blocked')
    declaration=next((c for c in blocking if c['name']=='Document purpose declarations'),None)
    if declaration:
        return result('sample_document','Sample document — not valid as original evidence','The first page or PDF metadata identifies this file as a sample, demonstration or unpublished article. It cannot substantiate an original publication or institutional evidence claim.','Upload the actual published article or an official issuer original. The current file remains flagged for reviewer investigation.','danger','blocked')
    conflicts=blocking or [c for c in warnings if c['name']=='Placement count comparison']
    if conflicts:
        return result('evidence_conflict','Not accepted — conflicting evidence',conflicts[0]['detail'],'Resolve the stated discrepancy with independent issuer evidence and an authorized reviewer.','danger','blocked')
    if document['status']=='verified' and latest and latest['outcome'] in ['verified','appeal_upheld'] and complete and issuer:
        return result('reviewer_verified','Verified by authorized review',latest['reason'],'The acceptance decision and supporting evidence are recorded in Activity & decisions.','success','accepted')
    if not complete:
        return result('checks_required','Full verification required','The current file does not have a completed run of the current verification checks.','Select Recheck now. File upload and fingerprinting alone do not authenticate a document.','neutral')
    if issuer:
        return result('issuer_match','Issuer original matched — awaiting approval',issuer['detail'],'An authorized reviewer must approve the institution, purpose and reporting period before this file is accepted.','neutral','awaiting_review')
    return result('issuer_evidence_required','Not verified — issuer evidence required','The checks finished, but no matching registered issuer original is available for this institution, category and reporting period. Public publication metadata cannot authenticate the uploaded file.','Provide the issuer original for a reviewer to register and compare. Missing issuer evidence does not mean the document is fake.')
