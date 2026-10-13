"""Replay the curated development corpus without exact-reference shortcuts.

Run: python evaluate_classification.py --output evaluation.json
Not a held-out benchmark: these documents were inspected during development.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from pypdf import PdfReader
from document_classification import classify,CLASSES,VERSION

def evaluate(root):
    rows=json.loads((root/'classification.json').read_text(encoding='utf-8'))['records']
    results=[];confusion=Counter();hashes={};families={}
    for row in rows:
        file=root/row['filename'];data=file.read_bytes()
        if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Changed source: '+row['id'])
        family=row['family_id'];split=row['split']
        if families.setdefault(family,split)!=split:raise ValueError('Source family crosses splits')
        if hashes.setdefault(row['sha256'],family)!=family:raise ValueError('Duplicate source crosses families')
        reader=PdfReader(file)
        # Match the application extraction limits; do not feed the curated class.
        text='\n'.join((p.extract_text() or '')[:5000] for p in reader.pages)[:50000]
        result=classify(text,'')
        predicted=result['class_id'] or result['state']
        confusion[(row['document_class'],predicted)]+=1
        results.append(dict(id=row['id'],expected=row['document_class'],predicted=predicted,
                            state=result['state'],split=split,family_id=family))
    return dict(classifier_version=VERSION,scope='development_corpus_replay',trained_model=False,
                held_out_accuracy=None,limitation='These documents were inspected during development. Exact-reference lookups are disabled here. Counts are diagnostic observations, not independent accuracy or fraud detection metrics.',
                documents=len(results),correct_type_count=sum(r['expected']==r['predicted'] for r in results),
                types_without_examples=[c['name'] for c in CLASSES.values() if not any(r['document_class']==c['id'] for r in rows)],
                confusion=[dict(expected=e,predicted=p,count=n) for (e,p),n in sorted(confusion.items())],results=results)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    result=evaluate(Path(__file__).with_name('datasets'))
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['scope','documents','correct_type_count','trained_model','held_out_accuracy']}))
