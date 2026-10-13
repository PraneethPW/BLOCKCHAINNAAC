# Veris document classification dataset

## Purpose and current release

This release adds document-type classification alongside the existing authenticity
assessment. A document may be an invoice and still be Genuine, Neutral or Fake.
Duplicate is a separate observation. Blockchain records do not classify documents.

The taxonomy has 23 category-specific types and one cross-category institutional
report type. The initial type-annotated corpus contains eight unchanged public
PDF originals: one example for each of the six categories and two NIRF reports.
The authenticity reference pack contains those eight originals and the existing
six explicitly fictional and six partial-evidence fixtures (20 files total).
The twelve generic fixtures are not silently assigned specific document types.

This is a small starter corpus. It has no independently adjudicated concealed
forgeries, no adequate examples for all types and no trained machine-learning
model. Empty types appear as "Needs documents" in the application. There is no
claimed training accuracy, fraud precision or fraud recall.

## Document types

| Category | Types |
| --- | --- |
| Teaching & faculty | Faculty qualification; appointment letter; faculty roster; training certificate |
| Research publications | Journal article; conference paper; patent record; research grant |
| Student placements | Offer letter; internship certificate; placement report |
| Infrastructure | Laboratory inventory; equipment invoice; building approval; facilities report |
| Student outcomes | Marksheet; degree certificate; graduation report; higher-studies admission |
| Financial records | Audited statement; invoice; fee receipt; grant utilisation certificate |
| Cross-category | Institutional report, including NIRF Overall reports |

## Baseline used by the application

`document_classification.py`, version 1.0, uses extracted text/OCR headings and
supporting fields. It does not classify from the uploaded filename or selected
category. Weak or ambiguous evidence produces an unassigned or multiple-type
result. Rule scores are not probability estimates. A mismatched submission
category is displayed separately and does not establish fraud.

An intact exact-file match to a curated type annotation supplies that reference's
type. This is a reference lookup, not generalisation by a learned model. These
type annotations cannot mark a document Genuine. The separate authenticity
engine checks its own provenance references, integrity and blocking evidence.

## Labels and evidence

Each classification record stores: immutable ID, filename, SHA-256, category,
document class, authenticity label, source origin, issuer, period, source URL,
retrieval time where known, source-family ID, parent reference, alteration,
assigned research split and a written basis for the label.

Genuine in the public-original corpus means the bytes were collected from the
named issuer/publisher over HTTPS. It does not independently establish every
reported fact, ownership by the uploader or institutional accreditation.
Legacy NIRF retrieval timestamps were not recorded; they remain null.

Reviewer annotations are attestations supported by the recorded evidence. They
are not automatically promoted to authenticity references. Manipulated samples
must identify a parent and a specific alteration. Parsed files cannot be labelled
Corrupted through the form. Blocking fictional/sample declarations prevent a
Genuine annotation. Duplicate hashes are rejected. All private annotations and
downloads remain restricted to authorised reviewers; ordinary users see public
seed records only.

## Collection needed before training

Collect independent, permissioned examples for each type from multiple issuers,
reporting years, layouts and scan qualities. Record the genuine source before
constructing any controlled alteration. Use explicit controlled labels and retain
the edit history. Obtain adjudicated fraud evidence for real-world fraud testing;
controlled alterations cannot substitute for that evidence. Do not publish
student marksheets, employee offers or private financial records without the
appropriate authority. Public source availability alone is not a licence for
unrestricted redistribution or model training.

The initial PDFs' canonical source links are in `classification.json`. Their
copyright remains with the respective issuers/publishers. Preserve attribution,
confirm reuse permissions and redact personal data before expanding any public
benchmark. The app does not transmit this classification corpus to OpenRouter.

## Splitting and evaluation

Assignments use stable SHA-256 buckets of the source-family ID: seven buckets
for train, two for validation and one for test. These are deterministic bucket
allocations, not a claim that this tiny corpus has exact 70/20/10 proportions.
All records from one issuer are grouped conservatively. An altered document
inherits its parent's group and split. Never move derivatives or re-exports to
another split. Curators must also check aliases and cross-issuer shared templates
before training; metadata alone cannot discover all such relationships.

Freeze a new independent evaluation set before training a learned classifier.
Report class counts, macro precision/recall/F1, confusion matrix, abstention rate
and performance by source. Evaluate document type and authenticity separately.
Never count exact reference memorisation as performance on unseen documents.

`python evaluate_classification.py --output evaluation.json` replays the current
development PDFs using content rules with exact lookups disabled. It verifies
hashes and source-family separation and records predicted versus annotated types.
Those documents were inspected during development, so its output is diagnostic
and explicitly does not report held-out accuracy.

## Reproducing application checks

Run `python -m pytest tests/test_classification.py tests/test_reference_dataset.py`.
The tests exercise real corpus bytes, classifications, independent authenticity
results, failed integrity checks, category mismatch, ambiguity, authorised labels,
account boundaries and inherited derivative splits. Provider calls in isolated
tests are disabled rather than mocked to return positive authenticity evidence.

Open Dataset references in Veris to inspect category coverage, filter the labelled
inventory, download originals and export CSV/JSON labels. Recheck older uploads
to add classification without rewriting their previous verification history.
