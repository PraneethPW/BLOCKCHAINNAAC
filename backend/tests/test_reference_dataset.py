import json
from types import SimpleNamespace
import pytest
import main,reference_dataset as dataset,verification
from test_workflow import account,upload

def test_manifest_exact_labels_and_changed_bytes(client):
    catalogue=dataset.manifest();assert len(catalogue['records'])==14
    with main.SessionLocal() as s:
        for record in catalogue['records']:
            doc=SimpleNamespace(category=record['category'],college='Own college',period='2025')
            data=(dataset.ROOT/record['filename']).read_bytes()
            result=dataset.compare(doc,data,s)
            assert result['state']=='matched' and result['label']==record['label']
            assert dataset.compare(doc,data+b'changed',s)['state']=='not_found'

def test_registration_requires_authorized_evidence_and_rejects_fake_genuine(client):
    owner=account(client);headers=account(client,'reviewer@example.com','reviewer')
    form=dict(label='genuine',college='Test College',category='Student placements',period='2025-26',reference='An independently established reference from the named issuer.')
    files={'file':('record.txt',b'Fictional document: 100 placements.','text/plain')}
    assert client.post('/dataset/records',headers=owner,data=form,files=files).status_code==403
    assert client.post('/dataset/records',headers=headers,data=form,files=files).status_code==409
    form['label']='fabricated';assert client.post('/dataset/records',headers=headers,data=form,files=files).status_code==201
    assert client.post('/dataset/records',headers=headers,data=form,files=files).status_code==409

def test_registered_dataset_genuine_context_and_integrity(client,monkeypatch):
    owner=account(client);reviewer=account(client,'reviewer@example.com','reviewer');data=b'Independent institutional record: 100 placements documented by issuer.'
    form=dict(label='genuine',college='Test College',category='Student placements',period='2025-26',reference='Issuer authenticated this exact original in independent correspondence REF-2026-001.')
    response=client.post('/dataset/records',headers=reviewer,data=form,files={'file':('record.txt',data,'text/plain')});assert response.status_code==201
    doc=upload(client,owner,data);client.post('/documents/'+doc['id']+'/verify',headers=owner);verification.process_next()
    result=client.get('/documents/'+doc['id'],headers=owner).json()
    assert result['verification_response']['outcome']=='genuine' and result['verification_response']['code']=='dataset_match'
    assert not result['job']['result']['assessment']['verification_eligible']
    with main.SessionLocal() as s:
        stored=s.get(main.Document,doc['id']);stored.period='wrong period'
        assert dataset.compare(stored,data,s)['state']=='not_found';s.rollback()
        source=s.get(dataset.DatasetRecord,response.json()['id']);(main.STORAGE/source.storage_name).write_bytes(b'changed')
        assert dataset.compare(stored,data,s)['state']=='unavailable'

def test_conflicting_labels_never_select_genuine(client):
    owner=account(client);reviewer=account(client,'reviewer@example.com','reviewer');data=b'Institutional record of a disputed claim with preserved reference.'
    for label in ['genuine','fabricated']:
        form=dict(label=label,college='Test College',category='Student placements',period='2025-26',reference='Independent correspondence establishing the referenced label REF-2026.')
        assert client.post('/dataset/records',headers=reviewer,data=form,files={'file':('record.txt',data,'text/plain')}).status_code==201
    doc=upload(client,owner,data);client.post('/documents/'+doc['id']+'/verify',headers=owner);verification.process_next()
    result=client.get('/documents/'+doc['id'],headers=owner).json()
    assert result['verification_response']['outcome']=='conflict'

def test_duplicate_is_separate_from_genuine_and_old_genuine_preserved(client):
    owner=account(client);record=dataset.manifest()['records'][0];data=(dataset.ROOT/record['filename']).read_bytes()
    for _ in range(2):
        uploaded=client.post('/documents?background=true',headers=owner,data={'category':'Infrastructure','period':'2025'},files={'file':(record['filename'],data,'application/pdf')}).json()
    doc=uploaded
    with main.SessionLocal() as s:
        d=s.get(main.Document,doc['id']);checks=[{'name':'Duplicate fingerprint','state':'warn','detail':'An identical submission exists.'},{'name':'Official institutional original comparison','state':'pass','detail':'Official bytes match.'}]
        d.checks=main.canonical(checks);d.status='verified'
        job=s.scalar(main.select(main.VerificationJob).where(main.VerificationJob.document_id==d.id));job.state='complete';job.result=main.canonical({'engine_version':'3.5','checks':checks});s.commit()
    result=client.get('/documents/'+doc['id'],headers=owner).json()
    assert result['verification_response']['outcome']=='genuine' and result['verification_response']['duplicate']

def test_seed_and_authorized_label_conflict_is_not_hidden(client):
    reviewer=account(client,'reviewer@example.com','reviewer');record=dataset.manifest()['records'][0];data=(dataset.ROOT/record['filename']).read_bytes()
    form=dict(label='neutral',college='Test College',category='Infrastructure',period='2025',reference='Independent conflicting reference preserved for investigation REF-001.')
    assert client.post('/dataset/records',headers=reviewer,data=form,files={'file':('original.pdf',data,'application/pdf')}).status_code==201
    with main.SessionLocal() as s:
        result=dataset.compare(SimpleNamespace(category='Infrastructure',college='Test College',period='2025'),data,s)
        assert result['state']=='conflict' and result['label'] is None
