"""Evidence-scoped checks. Signals are not automatic fraud verdicts."""
import io
import re
import unicodedata
from datetime import datetime, timezone
from pypdf import PdfReader

ENGINE_VERSION = '3.1'


def normal(value):
    return re.sub(r'\W+', ' ', unicodedata.normalize('NFKC', str(value)).lower()).strip()


def finding(name, state, detail, *, blocking=False, kind='authenticity'):
    return dict(name=name, state=state, detail=detail, blocking=blocking, kind=kind)


def ordered_dois(content):
    # Repair a DOI wrapped after a hyphen; never borrow DOI records from references.
    content = re.sub(r'(10\.\d{4,9}/\S*-)[ \t]*\n[ \t]*(?=[a-zA-Z0-9])', r'\1', content)
    values = []
    for value in re.findall(r'\b10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+', content):
        value = value.rstrip('.,;:)]}').lower()
        if value not in values:
            values.append(value)
    # Incomplete wrapped prefix must not become a second independent identifier.
    return [v for v in values if not v.endswith('-') and not any(x != v and x.startswith(v) for x in values)]


def claims(content, metadata):
    front = metadata.get('front_page_text') or content[:8000]
    boundary = re.search(r'^\s*(?:\d+[. ]+)?(?:references|bibliography|works cited|literature cited)\s*$', content, re.I | re.M)
    body = content[:boundary.start()] if boundary else content
    references = content[boundary.end():] if boundary else ''
    # Front-page DOI is only a claimed identifier; registry comparison still required.
    front_boundary = re.search(r'^\s*(?:references|bibliography|works cited)\s*$', front, re.I | re.M)
    front = front[:front_boundary.start()] if front_boundary else front
    primary = ordered_dois(front[:4500])
    cited = [d for d in ordered_dois(references) if d not in primary]
    unclassified = [d for d in ordered_dois(body) if d not in primary]
    pdf = metadata.get('pdf_metadata', {})
    title = pdf.get('Title', '')
    query_title = re.split(r'\s+[-–—|]\s+(?:educational|sample|demonstration)', title, flags=re.I)[0].strip()
    title_origin = 'PDF title metadata'
    if not query_title or normal(query_title) in ['untitled', 'document', 'microsoft word']:
        title_origin = 'First-page heading (inferred)'
        lines = []
        for line in front.splitlines()[:12]:
            line = line.strip()
            if re.match(r'^(?:abstract|authors?\b|references|educational\b|not a published\b|article type|prepared\b|doi\b|https?://)', line, re.I):break
            if len(line) >= 12 and not re.fullmatch(r'[\d\W]+', line):lines.append(line)
            if len(lines) == 2:break
        query_title = ' '.join(lines)
    query_title = query_title[:240]
    if len(normal(query_title).split()) < 3:query_title = ''
    return dict(front_matter=front[:4500], title=title, query_title=query_title, title_origin=title_origin, author=pdf.get('Author', ''), primary_dois=primary[:8], reference_dois=cited, unclassified_dois=unclassified, identifier_limit_exceeded=len(primary) > 8)


def declaration_checks(content, metadata):
    # Restrict to cover/front matter and metadata, not quotations in a bibliography.
    front = (metadata.get('front_page_text') or content[:6000])[:6000]
    context = normal(front + ' ' + ' '.join(metadata.get('pdf_metadata', {}).values()))
    phrases = ['educational sample', 'educational review sample', 'not a published article',
               'layout demonstration', 'writing demonstration', 'fictional document',
               'synthetic document', 'sample document', 'for demonstration only']
    hits = [phrase for phrase in phrases if phrase in context]
    result = finding('Document purpose declarations', 'warn' if hits else 'unknown',
                    'The cover or PDF metadata declares: ' + ', '.join(hits) + '. This conflicts with submission as original published or institutional evidence; review the claimed purpose.' if hits else
                    'No explicit demonstration declaration was detected. Its absence does not establish authenticity.', blocking=bool(hits))
    result['declarations'] = hits
    return [result]


def pdf_structure(data):
    checks = []
    if not data.startswith(b'%PDF-') or not re.search(rb'%%EOF\s*$', data):
        checks.append(finding('PDF structural integrity', 'warn', 'Missing PDF header or final end marker. The file may be truncated, corrupted, or contain appended data.', blocking=True, kind='integrity'))
    else:
        try:
            pdf = PdfReader(io.BytesIO(data), strict=True)
            if pdf.is_encrypted:
                raise ValueError('Encrypted PDF cannot be inspected')
            for page in pdf.pages:
                page.get_contents()
            checks.append(finding('PDF structural integrity', 'pass', 'Header, final end marker and strict PDF parsing succeeded. A structurally valid PDF can still be fabricated.', kind='integrity'))
        except Exception:
            checks.append(finding('PDF structural integrity', 'warn', 'Strict PDF parsing failed. Tolerant extraction does not establish a complete, uncorrupted file.', blocking=True, kind='integrity'))
    # Multiple revisions are common in legitimate workflows; never label them fraud.
    revisions = len(re.findall(rb'(?m)^startxref\s*$', data))
    checks.append(finding('PDF revision history', 'unknown', f'{revisions} cross-reference revision marker(s) detected. Incremental updates alone do not establish manipulation; compare issuer bytes and signed revisions.', kind='integrity'))
    return checks


def pdf_active_content(root):
    # /OpenAction can be a harmless page destination array, not executable code.
    unsafe=[]
    actions=[]
    if '/OpenAction' in root:actions.append(root['/OpenAction'])
    if '/AA' in root:actions.extend(root['/AA'].values())
    for action in actions:
        action=action.get_object() if hasattr(action,'get_object') else action
        if hasattr(action,'get') and action.get('/S') in ['/JavaScript','/Launch','/SubmitForm','/ImportData']:
            unsafe.append(str(action.get('/S')))
    if '/Names' in root and '/JavaScript' in root['/Names']:unsafe.append('JavaScript name tree')
    return [finding('PDF active content','warn','Executable or submission actions detected: '+', '.join(unsafe)+'. Inspect separately before accepting this file.',blocking=True,kind='integrity')] if unsafe else []


def signature_checks(data):
    """Validate signature bytes offline; do not fetch uploader-controlled AIA/CRL URLs."""
    try:
        # Do not treat a strict signature parser's inability to read an unsigned
        # PDF as a broken signature. Structure is assessed separately.
        fields=PdfReader(io.BytesIO(data)).get_fields() or {}
        if not any(field.get('/FT')=='/Sig' and field.get('/V') for field in fields.values()):
            return [finding('Cryptographic PDF signature', 'unknown', 'No embedded cryptographic signature. Visible stamps and signature images cannot authenticate the issuer.')]
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.validation import validate_pdf_signature
        from pyhanko_certvalidator import ValidationContext
        reader = PdfFileReader(io.BytesIO(data))
        signatures = reader.embedded_signatures
        if not signatures:
            return [finding('Cryptographic PDF signature', 'unknown', 'No embedded cryptographic signature. Visible stamps and signature images cannot authenticate the issuer.')]
        if len(signatures) > 5:
            return [finding('Cryptographic PDF signature', 'warn', 'More than five embedded signatures exceeds the validation limit; inspect separately.', blocking=True)]
        checks = []
        for index, signature in enumerate(signatures, 1):
            # This pass checks signed bytes only. Offline revocation gaps never
            # promote signer trust; the separate trust finding remains unknown.
            status = validate_pdf_signature(signature, signer_validation_context=ValidationContext(trust_roots=[], allow_fetching=False, revocation_mode='soft-fail'))
            intact = bool(status.intact and status.valid and status.docmdp_ok)
            checks.append(finding(f'Signed revision integrity {index}', 'pass' if intact else 'warn',
                                  'The signature validates the signed bytes and permitted modifications. Issuer identity and certificate trust remain unestablished.' if intact else
                                  'The embedded signature digest, cryptographic signature, or modification policy did not validate. Investigate changed signed content or invalid signing data.', blocking=not intact, kind='integrity'))
            checks.append(finding(f'Signer identity and revocation {index}', 'unknown', 'Issuer-approved trust roots and current revocation evidence are not configured. A self-signed or untrusted certificate cannot establish authenticity. No certificate URLs in the uploaded PDF were fetched.'))
        return checks
    except ImportError:
        return [finding('Cryptographic PDF signature', 'unknown', 'Signature validation dependency is unavailable. No signature authenticity was inferred.')]
    except Exception:
        return [finding('Cryptographic PDF signature', 'warn', 'Signature structures could not be validated. Obtain issuer validation before accepting this file.', blocking=True)]


def publication_checks(claim, results, category):
    if category != 'Research publications':
        return []
    checks = []
    if not claim['primary_dois']:
        detail = 'No article DOI was extracted from the cover/front matter. '
        detail += f"{len(claim['reference_dois'])} cited DOI(s) belong to the bibliography and were excluded from article authentication. "
        checks.append(finding('Article identity corroboration', 'unknown', detail + 'Obtain an issuer record; absence of a DOI does not prove fabrication.'))
        return checks
    if len(claim['primary_dois']) > 1:
        checks.append(finding('Article identifier ambiguity', 'unknown', 'Multiple front-page identifiers require review of article, dataset and related-resource roles.'))
    for doi in claim['primary_dois']:
        records = [r for r in results if r['identifier'] == doi and r['state'] == 'found']
        if not records:
            checks.append(finding('Article identity corroboration', 'unknown', f'{doi}: no available matching registry record. A provider outage or unindexed publication is not proof of fraud.'))
            continue
        record = next((r for r in records if r['provider'] == 'Crossref'), records[0])
        front = normal(claim['front_matter'])
        title = normal(record.get('title', ''))
        matches = bool(title and title in front)
        checks.append(finding('Article title versus registry', 'pass' if matches else 'warn',
                              f"DOI {doi}. Registry title: {record.get('title', '')}. " + ('The registry title appears in the cover/front matter. This is metadata consistency, not proof of an original file.' if matches else
                              'The registry title is absent from the cover/front matter. This may be a borrowed identifier, an OCR error or a different version; investigate.'), blocking=not matches))
        # PDF metadata is editable. A mismatch is evidence to investigate, not a verdict.
        pdf_title = normal(claim.get('title', ''))
        if pdf_title and pdf_title not in ('untitled', 'document') and len(pdf_title.split()) > 3 and title:
            checks.append(finding('PDF title metadata consistency', 'pass' if pdf_title == title else 'warn',
                                  'PDF title metadata agrees with the claimed DOI title.' if pdf_title == title else 'The editable PDF title metadata differs from the registry title; compare with the publisher original.', blocking=pdf_title != title))
        byline = claim['front_matter'][:2200]
        abstract = re.search(r'\babstract\b', byline, re.I)
        if abstract:
            byline = byline[:abstract.start()]
        byline = normal(byline + ' ' + claim.get('author', ''))
        surnames = [normal(a).split()[-1] for a in record.get('authors', []) if normal(a)]
        observed = [name for name in surnames if re.search(r'\b' + re.escape(name) + r'\b', byline)]
        checks.append(finding('Registry author names', 'pass' if observed else 'unknown',
                              f'{len(set(observed))} of {len(set(surnames))} registry author surnames observed in front matter or metadata. Name presence does not prove authorship or institutional affiliation.' if observed else
                              'Registry author names were not identified reliably in the front matter. Request issuer or author evidence.'))
        years = re.findall(r'\b(?:19|20)\d{2}\b', claim['front_matter'][:1600])
        if record.get('year') and years:
            match = str(record['year']) in years
            checks.append(finding('Publication year consistency', 'pass' if match else 'warn',
                                  f"Registry publication year: {record['year']}; front-matter years: {', '.join(dict.fromkeys(years))}. " + ('A matching year is present.' if match else 'No matching year was observed; inspect version and publication dates.'), blocking=not match))
        if any(r.get('notice') for r in records):
            checks.append(finding('Publication status notices', 'warn', 'A registry reports a retraction or withdrawal notice. Review its exact context before accepting the claim.', blocking=True))
    return checks


def assessment(checks):
    blocking = [c['name'] for c in checks if c.get('blocking') and c['state'] == 'warn']
    source = next((c for c in checks if c['name'] == 'Authorized source comparison'), {})
    supported = source.get('state') == 'pass'
    return dict(engine_version=ENGINE_VERSION, state='conflicting_evidence' if blocking else 'source_match_review_required' if supported else 'not_established',
                headline='Conflicting evidence requires investigation' if blocking else 'Issuer source bytes match; reviewer approval required' if supported else 'Authenticity has not been established',
                verification_eligible=supported and not blocking, blocking_checks=blocking,
                missing_evidence=[] if supported else ['Exact file comparison to a reviewer-registered issuer source for the same institution, category and period'],
                assessed_at=datetime.now(timezone.utc).isoformat(),
                explanation='Processing success and citation metadata are separate from authenticity. Blockchain preserves supported decisions; it does not determine whether a document is genuine.')
