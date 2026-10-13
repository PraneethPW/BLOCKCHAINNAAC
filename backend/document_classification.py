"""Explainable document-type baseline. Never an authenticity decision.

Rules are versioned and operate on extracted content, not filenames, selected
categories or authenticity labels. Scores are rule evidence, not probabilities.
"""
import re
import unicodedata

VERSION = '1.0'
CATEGORIES = ['Teaching & faculty', 'Research publications', 'Student placements',
              'Infrastructure', 'Student outcomes', 'Financial records']

# id, category index, display name, identifying phrases, supporting fields
RULES = [
    ('faculty_qualification',0,'Faculty qualification', ['faculty qualification','educational qualifications','academic qualifications'], ['ph.d','degree','university','qualification']),
    ('appointment_letter',0,'Appointment letter', ['appointment letter','letter of appointment','appointment order'], ['position','joining','salary','appointment']),
    ('faculty_roster',0,'Faculty roster', ['faculty list','list of faculty','faculty roster','details of faculty','faculty members'], ['designation','qualification','joining','department']),
    ('training_certificate',0,'Training certificate', ['faculty development programme','faculty development program','training certificate','certificate of participation'], ['participated','completed','training','certificate']),
    ('journal_article',1,'Journal article', ['research article','journal article','article','nature'], ['abstract','doi','references','received']),
    ('conference_paper',1,'Conference paper', ['conference paper','proceedings of','international conference','conference on'], ['abstract','references','doi','conference']),
    ('patent_record',1,'Patent record', ['patent specification','patent certificate','patent application','patent number'], ['inventor','applicant','claims','patent']),
    ('research_grant',1,'Research grant', ['research grant','sanction order','grant award'], ['principal investigator','project','sanctioned','funding']),
    ('offer_letter',2,'Offer letter', ['offer of employment','employment offer','offer letter'], ['position','joining','salary','employment']),
    ('internship_certificate',2,'Internship certificate', ['internship certificate','certificate of internship','internship completion'], ['completed','duration','internship','department']),
    ('placement_report',2,'Placement report', ['placement report','placement statistics','placement summary','final placements'], ['placed','recruiters','salary','offers']),
    ('laboratory_inventory',3,'Laboratory inventory', ['laboratory inventory','equipment list','list of equipment','lab inventory'], ['laboratory','quantity','qty','equipment']),
    ('equipment_invoice',3,'Equipment invoice', ['tax invoice','equipment invoice','invoice'], ['equipment','instrument','laboratory','serial number']),
    ('building_approval',3,'Building approval', ['building approval','building permit','approved building plan','building plan approval'], ['authority','building','permit','approval']),
    ('facilities_report',3,'Facilities report', ['facilities report','infrastructure report','physical facilities','campus facilities'], ['laboratories','classrooms','area','library']),
    ('marksheet',4,'Marksheet', ['statement of marks','marksheet','mark sheet','grade sheet','academic transcript'], ['semester','grade','marks','register number']),
    ('degree_certificate',4,'Degree certificate', ['degree certificate','provisional degree','degree of bachelor','degree of master'], ['awarded','university','degree','conferred']),
    ('graduation_report',4,'Graduation report', ['graduation report','pass percentage','graduation outcomes','examination results'], ['passed','appeared','students','year']),
    ('higher_studies_admission',4,'Higher-studies admission', ['admission offer','offer of admission','admission letter'], ['programme','program','university','admission']),
    ('audited_statement',5,'Audited statement', ['audited financial','annual accounts','audit report','financial statements','balance sheet'], ['auditor','income','expenditure','assets']),
    ('invoice',5,'Invoice', ['tax invoice','invoice'], ['invoice number','invoice no','total','amount']),
    ('fee_receipt',5,'Fee receipt', ['fee receipt','fees receipt','tuition receipt'], ['paid','amount','student','receipt']),
    ('grant_utilisation',5,'Grant utilisation certificate', ['utilisation certificate','utilization certificate'], ['grant','sanctioned','utilised','utilized']),
]

def taxonomy():
    return [dict(id=id,category=CATEGORIES[cat],name=name) for id,cat,name,_,_ in RULES]+[
        dict(id='institutional_report',category='Cross-category',name='Institutional report')]

CLASSES = {row['id']:row for row in taxonomy()}

def normalized(value):
    return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',value).casefold()).strip()

def contains(text, phrase):
    return bool(re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)',text))

def classify(content, selected_category='', reference=None):
    """Reference can supply an intact curated type; it cannot supply authenticity."""
    base=dict(version=VERSION,method='content_rules',state='unclassified',class_id=None,
              label='Document type not identified',category=None,category_matches=None,
              evidence=[],alternatives=[],score=None,
              explanation='Readable content does not provide enough document-type evidence.',
              scope='Document type only. Authenticity is assessed separately.')
    if reference and reference.get('document_class') in CLASSES:
        row=CLASSES[reference['document_class']]
        return dict(base,state='classified',method='curated_exact_reference',class_id=row['id'],
                    label=row['name'],category=row['category'],
                    category_matches=True if row['category']=='Cross-category' else row['category']==selected_category,
                    evidence=['Exact SHA-256 match to curated type annotation '+reference['id']],
                    explanation='The unchanged reference file has a recorded document-type annotation.')
    body=normalized(content[:30000]);heading=body[:1800]
    if len(body)<40:return base
    if ('national institutional ranking framework' in heading or 'nirf' in heading) and 'ministry' in heading:
        return dict(base,state='classified',class_id='institutional_report',label='Institutional report',
                    category='Cross-category',category_matches=True,evidence=['NIRF institutional report heading'],
                    explanation='A report covering multiple institutional categories; not a single certificate or invoice.')
    candidates=[]
    for id,cat,name,phrases,fields in RULES:
        titles=[p for p in phrases if contains(heading,p)]
        support=[p for p in fields if contains(body,p)]
        # Incidental mentions deep in reports must not classify the entire file.
        if not titles or len(support)<2:continue
        score=4+min(len(support),4)
        if any(contains(body[:250],p) for p in titles):score+=2
        candidates.append(dict(class_id=id,label=name,category=CATEGORIES[cat],score=score,
                               evidence=['Heading: '+p for p in titles[:2]]+['Field: '+p for p in support[:4]]))
    # Equipment invoice is a specific invoice; don't report it as an ambiguity.
    if any(c['class_id']=='equipment_invoice' for c in candidates):
        candidates=[c for c in candidates if c['class_id']!='invoice']
    candidates.sort(key=lambda c:(-c['score'],c['class_id']))
    if not candidates:return base
    first=candidates[0];base['alternatives']=[{k:c[k] for k in ['class_id','label','category','score']} for c in candidates[:3]]
    if len(candidates)>1 and first['score']-candidates[1]['score']<2:
        return dict(base,state='ambiguous',label='Multiple document types detected',
                    explanation='Several types have similar content evidence. No single type was forced.')
    return dict(base,**first,state='classified',category_matches=first['category']==selected_category,
                explanation='Identified from document headings and supporting fields. Rule score is not a confidence percentage.')
