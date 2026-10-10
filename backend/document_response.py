"""Automatic, evidence-scoped document outcomes, separate from fraud adjudication."""
from authenticity import ENGINE_VERSION


def verification_response(document):
    checks=document['checks'];job=document.get('job');decisions=document.get('decisions',[])
    latest=decisions[-1] if decisions else None
    blocking=[c for c in checks if c['state']=='warn' and (c.get('blocking') or c['name']=='Placement count comparison')]
    warnings=[c for c in checks if c['state']=='warn']
    issuer=next((c for c in checks if c['name']=='Authorized source comparison' and c['state']=='pass'),None)
    complete=bool(job and job['state']=='complete' and job['result'].get('engine_version')==ENGINE_VERSION)

    def result(code,title,reason,action,tone='neutral',acceptance='not_verified',outcome='neutral',mode='automated'):
        return dict(code=code,title=title,reason=reason,action=action,tone=tone,acceptance=acceptance,
                    outcome=outcome,mode=mode,analysis_complete=complete,
                    checked_at=job['updated_at'] if job else document.get('created_at'),
                    findings=[c['name'] for c in warnings])

    if job and job['state'] in ['queued','running']:
        return result('checking','Checking your document',job['stage'],'The assessment appears automatically when the checks finish.','running','processing','checking')
    changed=next((c for c in blocking if c.get('integrity_failure')=='changed' or
                  (c['name']=='Original file integrity and processing' and 'fingerprint differs' in c['detail'].lower())),None)
    if changed:
        return result('integrity_failed','Manipulated — stored file changed',changed['detail'],
                      'Replace this stored copy with the original submitted file. This proves a change after upload; it does not identify who changed it.','danger','blocked','manipulated')
    if document['status']=='confirmed_fraud' and latest and latest['outcome']=='confirmed_fraud':
        return result('fraud_confirmed','Fraud confirmed by authorized review',latest['reason'],
                      'The historical decision and supporting evidence are retained. Corrections use a linked appeal.','danger','confirmed_fraud','fraud_confirmed','reviewer')
    if job and job['state']=='failed':
        if job['result'].get('failure_category')=='corrupted':
            return result('corrupted_file','Corrupted — invalid file structure',job['error'],
                          'Upload a fresh, readable original. The file failed its format integrity inspection.','danger','blocked','corrupted')
        return result('check_failed','Neutral',job['error'],
                      'Retry the inspection or provide an unlocked, supported original. No genuine or fake classification was assigned.','neutral','not_verified')
    structural=next((c for c in blocking if c['name']=='PDF structural integrity'),None)
    if structural:
        return result('corrupted_file','Corrupted / structurally invalid PDF',structural['detail'],
                      'Obtain an intact original PDF. Readable text does not repair the failed structural check.','danger','blocked','corrupted')
    declaration=next((c for c in blocking if c['name']=='Document purpose declarations'),None)
    if declaration:
        fabricated=any(p in declaration.get('declarations',[]) for p in ['fictional document','synthetic document'])
        return result('sample_document','Fabricated — declared fictional document' if fabricated else 'Non-original — sample document',
                      'The first page or PDF metadata explicitly declares a fictional or synthetic document.' if fabricated else
                      'The first page or PDF metadata identifies a sample, demonstration or unpublished article. This is not original publication or institutional evidence.',
                      'Use the actual published article or official issuer original. A declared sample is not proof of deliberate fraud.','danger','blocked','fabricated' if fabricated else 'non_original')
    if blocking:
        return result('evidence_conflict','Conflicting evidence',blocking[0]['detail'],
                      'Compare the stated discrepancy with an independent issuer original. This assessment identifies a conflict, not deliberate fraud.','danger','blocked','conflict')
    if not complete:
        return result('checks_required','Neutral','This file has not completed the current automated inspection.',
                      'Select Recheck now to run the current automatic checks.')
    if issuer:
        if document['status']=='verified' and latest and latest['outcome'] in ['verified','appeal_upheld']:
            return result('reviewer_verified','Verified by authorized review',latest['reason'],
                          'The recorded decision and independent issuer comparison are available in Activity & decisions.','success','accepted','genuine','reviewer')
        return result('issuer_match','Genuine — matches registered issuer original',issuer['detail'],
                      'Automatic file verification is complete. This confirms an exact match to the registered issuer file; institutional ownership and accreditation claims are separate.','success','accepted','genuine')
    return result('issuer_evidence_required','Neutral',
                  'Checks completed. No decisive authenticity evidence was found. The available public records do not prove or disprove that this uploaded file is genuine.',
                  'No action is required to finish this assessment. An independent issuer original can provide a stronger result later.')
