import asyncio
from authenticity import claims, declaration_checks, publication_checks, assessment, ordered_dois, pdf_structure, pdf_active_content


def test_reference_dois_cannot_authenticate_an_article():
    content='Learning from graphs with graph neural networks\nEducational sample\nNot a published article\nReferences\nArray programming with NumPy https://doi.org/10.1038/s41586-020-2649-2'
    claim=claims(content,{})
    assert claim['primary_dois']==[]
    assert claim['reference_dois']==['10.1038/s41586-020-2649-2']
    checks=declaration_checks(content,{})+publication_checks(claim,[],'Research publications')
    assert assessment(checks)['state']=='conflicting_evidence'
    assert not assessment(checks)['verification_eligible']


def test_borrowed_front_page_doi_with_wrong_title_blocks_acceptance():
    claim=claims('Invented research on graphs\n10.1038/s41586-020-2649-2\nAuthor: Invented Person\n2026',{})
    records=[dict(identifier='10.1038/s41586-020-2649-2',state='found',provider='Crossref',title='Array programming with NumPy',authors=['Charles R. Harris'],year=2020)]
    checks=publication_checks(claim,records,'Research publications')
    assert any(c['name']=='Article title versus registry' and c['state']=='warn' and c['blocking'] for c in checks)
    assert any(c['name']=='Publication year consistency' and c['state']=='warn' for c in checks)
    assert assessment(checks)['state']=='conflicting_evidence'


def test_matching_publication_metadata_still_does_not_authenticate_bytes():
    claim=claims('Array programming with NumPy\nCharles R. Harris\n2020\nhttps://doi.org/10.1038/s41586-020-2649-2',{})
    records=[dict(identifier='10.1038/s41586-020-2649-2',state='found',provider='Crossref',title='Array programming with NumPy',authors=['Charles R. Harris'],year=2020)]
    checks=publication_checks(claim,records,'Research publications')
    assert any(c['name']=='Article title versus registry' and c['state']=='pass' for c in checks)
    assert assessment(checks)['state']=='not_established'
    assert not assessment(checks)['verification_eligible']


def test_provider_unavailability_and_absence_do_not_mean_fraud():
    claim=claims('An article\n10.1234/example',{})
    for state in ['not_found','unavailable']:
        checks=publication_checks(claim,[dict(identifier='10.1234/example',state=state)],'Research publications')
        assert all(c['state']=='unknown' for c in checks)
        assert assessment(checks)['state']=='not_established'


def test_metadata_demonstration_declaration_overrides_a_source_match():
    checks=declaration_checks('Paper body',{'pdf_metadata':{'Author':'Generated for layout demonstration'}})
    checks.append(dict(name='Authorized source comparison',state='pass'))
    assert assessment(checks)['verification_eligible'] is False


def test_wrapped_doi_is_repaired_and_reference_heading_is_scoped():
    assert ordered_dois('10.1038/s41586-020-\n2649-2')==['10.1038/s41586-020-2649-2']
    assert claims('Paper\nBibliography\n10.1234/reference',{})['primary_dois']==[]


def test_corrupt_pdf_never_passes_structural_integrity():
    for data in [b'not pdf',b'%PDF-1.7\ntruncated',b'%PDF-1.7\ninvalid objects\n%%EOF']:
        checks=pdf_structure(data)
        assert checks[0]['state']=='warn' and checks[0]['blocking']


def test_page_destination_is_not_misclassified_as_executable_content():
    assert pdf_active_content({'/OpenAction':[1,'/Fit']})==[]
    assert pdf_active_content({'/OpenAction':{'/S':'/GoTo','/D':[1,'/Fit']}})==[]
    assert pdf_active_content({'/OpenAction':{'/S':'/JavaScript','/JS':'app.alert(1)'}})[0]['blocking']


def test_bibliography_only_job_never_queries_article_registries(client,monkeypatch):
    # Uses the integration fixture in test_workflow via conftest below.
    from test_workflow import account
    import verification
    h=account(client)
    content=b'Learning from graphs\nEducational sample\nNot a published article\nReferences\n10.1038/s41586-020-2649-2'
    async def forbidden(*args):
        raise AssertionError('Reference DOI must not launch article authentication')
    monkeypatch.setattr(verification,'corroborate',forbidden)
    r=client.post('/documents?background=true',headers=h,data={'category':'Research publications','period':'2026'},files={'file':('sample.txt',content,'text/plain')})
    verification.process_next()
    document=client.get('/documents/'+r.json()['id'],headers=h).json()
    assert document['status']=='flagged'
    assert document['job']['state']=='complete'
    assert document['job']['result']['sources']==[]
    assert document['job']['result']['assessment']['state']=='conflicting_evidence'
    client.post('/documents/'+r.json()['id']+'/recheck',headers=h)
    assert client.get('/documents/'+r.json()['id'],headers=h).json()['status']=='flagged'


def test_review_cannot_accept_without_current_processing_and_issuer_source(client):
    from test_workflow import account,upload
    import verification
    owner=account(client)
    reviewer=account(client,'reviewer@example.com','reviewer')
    doc=upload(client,owner)
    body={'outcome':'verified','reason':'A substantive review reason is provided here.','evidence':'A claimed reference alone is not a source.'}
    endpoint='/documents/'+doc['id']+'/decisions'
    assert client.post(endpoint,headers=reviewer,json=body).status_code==409
    client.post('/documents/'+doc['id']+'/verify',headers=owner)
    verification.process_next()
    assert client.post(endpoint,headers=reviewer,json=body).status_code==409
    client.post('/trusted-records',headers=reviewer,data={'college':'Test College','category':'Student placements','period':'2025-26','issuer':'Test Issuer','reference':'Authorized source reference REF-100'},files={'file':('issuer.txt',b'Claim: 100 placements; needs corroboration.','text/plain')})
    import main
    from sqlalchemy import select
    with main.SessionLocal() as s:
        source=s.scalar(select(main.SourceRecord));original=(main.STORAGE/source.storage_name).read_bytes()
        (main.STORAGE/source.storage_name).write_bytes(b'Altered issuer file')
    assert client.post(endpoint,headers=reviewer,json=body).status_code==409
    with main.SessionLocal() as s:
        source=s.scalar(select(main.SourceRecord));(main.STORAGE/source.storage_name).write_bytes(original)
    assert client.post(endpoint,headers=reviewer,json=body).json()['status']=='verified'


def test_signed_byte_validation_catches_changed_bytes_without_trusting_self_signed_issuer():
    # Ephemeral in-memory test fixture, never a production document or issuer.
    import io
    from datetime import datetime,timedelta,timezone
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from asn1crypto import x509 as asn_x509,keys
    from pyhanko.sign import signers
    from pyhanko_certvalidator.registry import SimpleCertificateStore
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pypdf import PdfWriter
    from authenticity import signature_checks
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Local integrity regression')])
    now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=1)).add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True).sign(key,hashes.SHA256()))
    signer=signers.SimpleSigner(signing_cert=asn_x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER)),signing_key=keys.PrivateKeyInfo.load(key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())),cert_registry=SimpleCertificateStore())
    writer=PdfWriter();writer.add_blank_page(width=300,height=300);writer.add_metadata({'/Title':'Original regression title'})
    original=io.BytesIO();writer.write(original)
    signed=signers.sign_pdf(IncrementalPdfFileWriter(io.BytesIO(original.getvalue())),signature_meta=signers.PdfSignatureMetadata(field_name='EvidenceSignature'),signer=signer).getvalue()
    good=signature_checks(signed)
    assert any(c['name']=='Signed revision integrity 1' and c['state']=='pass' for c in good),good
    assert any(c['name']=='Signer identity and revocation 1' and c['state']=='unknown' for c in good)
    changed=signed.replace(b'Original regression title',b'Modified regression title',1)
    assert changed!=signed and len(changed)==len(signed)
    bad=signature_checks(changed)
    assert any(c['blocking'] and c['state']=='warn' for c in bad),bad
