import copy
import hashlib
import io
import json
import pytest
from pypdf import PdfReader
import main,verification
import classification_dataset as corpus
from document_classification import classify,CLASSES
from test_workflow import account,upload


def test_rules_do_not_use_selected_category_or_authenticity():
    text='Equipment invoice\nLaboratory instrument serial number 100. Total amount 4000. Invoice number 42.'
    result=classify(text,'Student outcomes')
    assert result['class_id']=='equipment_invoice' and result['category_matches'] is False
    assert 'authenticity_label' not in result and 'outcome' not in result
    assert classify(text,'Infrastructure')['category_matches'] is True
    assert classify('Hello, this is a meeting invitation for next week.','Financial records')['state']=='unclassified'
    assert classify('','Research publications')['state']=='unclassified'


def test_ambiguous_packet_and_incidental_mentions_not_forced():
    text='Offer letter and appointment letter. Position: lecturer; salary 100; joining Monday; employment begins next month.'
    assert classify(text)['state']=='ambiguous'
    text='General meeting minutes. '+('Discussion of institutional policy. '*120)+' Tax invoice: Total amount; invoice number 12.'
    assert classify(text)['state']=='unclassified'


def test_taxonomy_all_categories_and_reference_family_split():
    from document_classification import CATEGORIES
    assert len(CLASSES)==24
    assert all(any(c['category']==category for c in CLASSES.values()) for category in CATEGORIES)
    rows=corpus.seed_records();assert len(rows)==8
    assert all(r['integrity']=='intact' for r in rows)
    assert {r['category'] for r in rows}==set(CATEGORIES+['Cross-category'])
    for row in rows:
        data=(corpus.ROOT/row['filename']).read_bytes()
        assert classify('',row['category'],corpus.matched_type(data))['class_id']==row['document_class']
        assert corpus.matched_type(data+b'changed') is None
    broken=copy.deepcopy(rows);broken[0]['split']='test' if broken[0]['split']!='test' else 'train'
    with pytest.raises(ValueError):corpus.validated(broken)
    broken=copy.deepcopy(rows);broken.append({**rows[0],'family_id':'different-family'})
    with pytest.raises(ValueError):corpus.validated(broken)


def test_api_auth_coverage_exports_and_download_integrity(client,monkeypatch,tmp_path):
    client.cookies.clear();assert client.get('/classification/catalogue').status_code==401
    h=account(client)
    data=client.get('/classification/catalogue',headers=h).json()
    assert data['trained_model'] is False and data['evaluation']['accuracy'] is None
    assert any(c['documents']==0 for g in data['coverage'] for c in g['classes'])
    assert len(client.get('/classification/export',headers=h).json()['records'])==8
    assert client.get('/classification/export?format=csv',headers=h).text.startswith('id,filename,sha256,')
    assert client.get('/classification/export?format=xml',headers=h).status_code==400
    row=data['records'][0]
    file=client.get('/classification/files/'+row['id'],headers=h)
    assert hashlib.sha256(file.content).hexdigest()==row['sha256']
    monkeypatch.setattr(corpus,'ROOT',tmp_path)
    assert client.get('/classification/files/'+row['id'],headers=h).status_code==409


def test_annotation_authorization_derivatives_and_private_scope(client):
    owner=account(client);reviewer=account(client,'reviewer@example.com','reviewer')
    form=dict(document_class='offer_letter',authenticity_label='neutral',issuer='Example Employer',period='2026',label_evidence='An unresolved employment offer received with no independent issuer confirmation.')
    content=b'Offer letter. Employment position developer. Salary amount 40000 and joining 1 June.'
    assert client.post('/classification/records',headers=owner,data=form,files={'file':('offer.txt',content)}).status_code==403
    response=client.post('/classification/records',headers=reviewer,data=form,files={'file':('offer.txt',content)})
    assert response.status_code==201,response.text
    original=response.json()
    assert client.post('/classification/records',headers=reviewer,data=form,files={'file':('renamed.txt',content)}).status_code==409
    assert not any(r['id']==original['id'] for r in client.get('/classification/catalogue',headers=owner).json()['records'])
    assert client.get('/classification/files/'+original['id'],headers=owner).status_code==404
    form['authenticity_label']='manipulated'
    assert client.post('/classification/records',headers=reviewer,data=form,files={'file':('changed.txt',content+b' altered')}).status_code==400
    form.update(parent_id=original['id'],alteration='Controlled edit replacing the salary amount from 40000 to 90000.')
    response=client.post('/classification/records',headers=reviewer,data=form,files={'file':('changed.txt',content.replace(b'40000',b'90000'))})
    assert response.status_code==201,response.text
    assert response.json()['family_id']==original['family_id'] and response.json()['split']==original['split']
    # A dataset type annotation must never grant authenticity to the uploaded file.
    doc=upload(client,owner,content);client.post('/documents/'+doc['id']+'/verify',headers=owner);verification.process_next()
    result=client.get('/documents/'+doc['id'],headers=owner).json()
    assert result['verification_response']['outcome']=='neutral'
    assert result['job']['result']['metadata']['classification']['class_id']=='offer_letter'


def test_genuine_annotation_rejects_fiction_and_false_corruption(client):
    h=account(client,'reviewer@example.com','reviewer')
    form=dict(document_class='offer_letter',authenticity_label='genuine',issuer='Example Employer',period='2026',label_evidence='An independently collected original, purportedly confirmed by the named issuer.')
    response=client.post('/classification/records',headers=h,data=form,files={'file':('fake.txt',b'Fictional document. Offer letter for an invented employee.')})
    assert response.status_code==409
    form['authenticity_label']='corrupted'
    assert client.post('/classification/records',headers=h,data=form,files={'file':('ok.txt',b'Readable original')}).status_code==409
    assert client.post('/classification/records',headers=h,data=form,files={'file':('broken.pdf',b'%PDF-1.7 broken')}).status_code==201


def test_seed_and_new_examples_share_canonical_issuer_family(client):
    h=account(client,'reviewer@example.com','reviewer')
    seed=corpus.seed_records()[0]
    form=dict(document_class=seed['document_class'],authenticity_label='neutral',issuer=seed['issuer'].upper(),period='2026',
              label_evidence='Independent example from the same issuer, with no confirmed authenticity label.')
    response=client.post('/classification/records',headers=h,data=form,files={'file':('another.txt',b'Independent document for source family grouping.')})
    assert response.status_code==201,response.text
    assert response.json()['family_id']==seed['family_id']
    assert response.json()['split']==seed['split']


@pytest.mark.parametrize('index',range(6))
def test_public_original_type_and_genuine_independently(client,monkeypatch,index):
    # Providers are disabled for deterministic tests; authenticity comes from the
    # downloaded, hashed public original, never a mocked positive provider response.
    async def absent(*args,**kwargs):return {'state':'not_applicable','detail':'No external lookup during isolated regression.'}
    async def no_records(*args,**kwargs):return []
    monkeypatch.setattr(verification,'compare_publisher_original',absent)
    monkeypatch.setattr(verification,'compare_institutional_original',absent)
    monkeypatch.setattr(verification,'corroborate',no_records)
    monkeypatch.setattr(verification,'discover_title',no_records)
    h=account(client);row=corpus.seed_records()[index];data=(corpus.ROOT/row['filename']).read_bytes()
    doc=client.post('/documents?background=true',headers=h,data={'category':row['category'],'period':row['period']},files={'file':('renamed.pdf',data,'application/pdf')}).json()
    verification.process_next()
    result=client.get('/documents/'+doc['id'],headers=h).json()
    assert result['job']['state']=='complete',result['job']
    assert result['job']['result']['metadata']['classification']['class_id']==row['document_class']
    assert result['verification_response']['outcome']=='genuine',result['verification_response']
    report=client.get('/documents/'+doc['id']+'/report',headers=h)
    assert 'Document type classification' in '\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(report.content)).pages)
