# How Veris works inside {#veris-architecture}

Veris is a React application backed by one FastAPI service. SQL stores accounts, evidence metadata, jobs and decisions; original files stay on disk. Background workers compare evidence and save results that the browser reloads.

- Follow the upload journey from a button click to a saved assessment and back to the screen.
- Authentication checks both a signed cookie and a revocable database session.
- File authenticity, institutional claim support, AI advice and blockchain storage have separate rules.
- Open a diagram to explore nodes and arrows. Select the guided steps to highlight each part; hover source citations for pinned code.

@answer scope="Repository architecture · not live network activity"
@meta locale=en quality_profile=showcase repo_url=https://github.com/PraneethPW/BLOCKCHAINNAAC.git repo_revision=e27a6ed7cd2c57bd769065985c790bdb926497fe

@source ui title="frontend/src/App.tsx:34–59" path=frontend/src/App.tsx lines=34:59
@source authui title="frontend/src/App.tsx:28–31" path=frontend/src/App.tsx lines=28:31
@source transport title="frontend/src/api.ts:1–8" path=frontend/src/api.ts lines=1:8
@source proxy title="frontend/vite.config.ts:1–4" path=frontend/vite.config.ts lines=1:4
@source hosted title="frontend/vercel.json:1–1" path=frontend/vercel.json lines=1:1
@source db title="backend/main.py:28–44" path=backend/main.py lines=28:44
@source models title="backend/main.py:48–174" path=backend/main.py lines=48:174
@source auth title="backend/main.py:175–202" path=backend/main.py lines=175:202
@source guards title="backend/main.py:359–383" path=backend/main.py lines=359:383
@source login title="backend/main.py:412–449" path=backend/main.py lines=412:449
@source upload title="backend/main.py:311–324" path=backend/main.py lines=311:324
@source handlers title="backend/main.py:450–489" path=backend/main.py lines=450:489
@source serialize title="backend/main.py:204–247" path=backend/main.py lines=204:247
@source checks title="backend/main.py:251–291" path=backend/main.py lines=251:291
@source lifespan title="backend/main.py:325–358" path=backend/main.py lines=325:358
@source worker title="backend/verification.py:144–229" path=backend/verification.py lines=144:229
@source inspect title="backend/verification.py:31–101" path=backend/verification.py lines=31:101
@source public title="backend/verification.py:103–142" path=backend/verification.py lines=103:142
@source search title="backend/source_discovery.py:13–71" path=backend/source_discovery.py lines=13:71
@source publisher title="backend/publisher_original.py:39–69" path=backend/publisher_original.py lines=39:69
@source nirf title="backend/institutional_original.py:62–88" path=backend/institutional_original.py lines=62:88
@source outcome title="backend/document_response.py:5–76" path=backend/document_response.py lines=5:76
@source rules title="backend/authenticity.py:201–214" path=backend/authenticity.py lines=201:214
@source workspace title="backend/main.py:621–674" path=backend/main.py lines=621:674
@source claimsui title="frontend/src/AccreditationConsole.tsx:38–63" path=frontend/src/AccreditationConsole.tsx lines=38:63
@source claims title="backend/accreditation.py:91–149" path=backend/accreditation.py lines=91:149
@source claimcompare title="backend/accreditation.py:24–61" path=backend/accreditation.py lines=24:61
@source decisions title="backend/main.py:507–532" path=backend/main.py lines=507:532
@source seal title="backend/accreditation.py:152–167" path=backend/accreditation.py lines=152:167
@source audit title="backend/accreditation.py:218–240" path=backend/accreditation.py lines=218:240
@source chainproof title="backend/ledger_proof.py:49–82" path=backend/ledger_proof.py lines=49:82
@source anchorworker title="backend/anchor_worker.py:16–79" path=backend/anchor_worker.py lines=16:79
@source ledgercontract title="contracts/VerisLedger.sol:5–43" path=contracts/VerisLedger.sol lines=5:43
@source aiui title="frontend/src/EvidenceDetail.tsx:64–77" path=frontend/src/EvidenceDetail.tsx lines=64:77
@source ai title="backend/main.py:533–552" path=backend/main.py lines=533:552
@source report title="backend/main.py:557–619" path=backend/main.py lines=557:619
@source trusted title="backend/main.py:490–506" path=backend/main.py lines=490:506
@source walletui title="frontend/src/WalletConsole.tsx:17–44" path=frontend/src/WalletConsole.tsx lines=17:44
@source walletconnection title="frontend/src/walletConnection.ts:3–24" path=frontend/src/walletConnection.ts lines=3:24
@source walletmodels title="backend/wallet.py:23–56" path=backend/wallet.py lines=23:56
@source challenge title="backend/wallet.py:109–169" path=backend/wallet.py lines=109:169
@source crypt title="backend/wallet.py:86–102" path=backend/wallet.py lines=86:102
@source walletread title="backend/wallet.py:177–229" path=backend/wallet.py lines=177:229
@source vaultworker title="backend/wallet_worker.py:79–130" path=backend/wallet_worker.py lines=79:130
@source vaultproof title="backend/wallet_worker.py:23–57" path=backend/wallet_worker.py lines=23:57
@source vaultcontract title="contracts/VerisVault.sol:5–20" path=contracts/VerisVault.sol lines=5:20
@source workerflags title="backend/wallet_runtime.py:4–9" path=backend/wallet_runtime.py lines=4:9
@source datasetui title="frontend/src/DatasetConsole.tsx:9–16" path=frontend/src/DatasetConsole.tsx lines=9:16
@source dataset title="backend/reference_dataset.py:12–76" path=backend/reference_dataset.py lines=12:76
@source classui title="frontend/src/ClassificationConsole.tsx:12–16" path=frontend/src/ClassificationConsole.tsx lines=12:16
@source classrecords title="backend/classification_dataset.py:26–84" path=backend/classification_dataset.py lines=26:84
@source classroutes title="backend/classification_dataset.py:86–178" path=backend/classification_dataset.py lines=86:178
@source classify title="backend/document_classification.py:52–92" path=backend/document_classification.py lines=52:92
@source migrations title="backend/schema_migrations.py:5–52" path=backend/schema_migrations.py lines=5:52
@source entry title="frontend/src/main.tsx:1–6" path=frontend/src/main.tsx lines=1:6
@source table-account title="veris_accounts model" path=backend/main.py lines=48:55
@source table-document title="veris_documents model" path=backend/main.py lines=56:70
@source table-decision title="veris_decisions model" path=backend/main.py lines=71:80
@source table-sourcerecord title="veris_sources model" path=backend/main.py lines=81:92
@source table-anchor title="veris_anchors model" path=backend/main.py lines=93:104
@source table-sourcemetric title="veris_source_metrics model" path=backend/main.py lines=105:110
@source table-networkconfig title="veris_network_config model" path=backend/main.py lines=111:115
@source table-authsession title="veris_auth_sessions model" path=backend/main.py lines=116:121
@source table-reviewerinvite title="veris_reviewer_invites model" path=backend/main.py lines=122:126
@source table-archive title="veris_archived_records model" path=backend/main.py lines=127:132
@source table-verificationjob title="veris_verification_jobs model" path=backend/main.py lines=133:144
@source table-accreditationclaim title="veris_accreditation_claims model" path=backend/main.py lines=146:155
@source table-claimreview title="veris_claim_reviews model" path=backend/main.py lines=157:166
@source table-evidencesnapshot title="veris_evidence_snapshots model" path=backend/main.py lines=168:174
@source route-main-health title="GET /health" path=backend/main.py lines=406:411
@source route-main-register title="POST /auth/register" path=backend/main.py lines=412:423
@source route-main-sign_in title="POST /auth/login" path=backend/main.py lines=424:433
@source route-main-me title="GET /auth/me" path=backend/main.py lines=434:435
@source route-main-logout title="POST /auth/logout" path=backend/main.py lines=436:443
@source route-main-change_password title="POST /auth/password" path=backend/main.py lines=444:449
@source route-main-list_documents title="GET /documents" path=backend/main.py lines=450:453
@source route-main-upload title="POST /documents" path=backend/main.py lines=454:471
@source route-main-detail title="GET /documents/{id}" path=backend/main.py lines=472:473
@source route-main-original title="GET /documents/{id}/file" path=backend/main.py lines=474:480
@source route-main-recheck title="POST /documents/{id}/recheck" path=backend/main.py lines=481:483
@source route-main-enqueue_verification title="POST /documents/{id}/verify" path=backend/main.py lines=484:489
@source route-main-source_record title="POST /trusted-records" path=backend/main.py lines=490:506
@source route-main-decide title="POST /documents/{id}/decisions" path=backend/main.py lines=507:532
@source route-main-assist title="POST /documents/{id}/ai" path=backend/main.py lines=533:552
@source route-main-ledger title="GET /ledger" path=backend/main.py lines=553:556
@source route-main-evidence_report title="GET /documents/{id}/report" path=backend/main.py lines=557:619
@source route-main-workspace title="GET /workspace" path=backend/main.py lines=636:654
@source route-main-events title="GET /events" path=backend/main.py lines=656:674
@source route-main-source_file title="GET /trusted-records/{id}/file" path=backend/main.py lines=676:682
@source table-walletbinding title="veris_wallet_bindings model" path=backend/wallet.py lines=23:27
@source table-walletchallenge title="veris_wallet_challenges model" path=backend/wallet.py lines=29:37
@source table-walletdocument title="veris_wallet_documents model" path=backend/wallet.py lines=39:56
@source route-wallet-challenge title="POST /wallet/challenge" path=backend/wallet.py lines=126:146
@source route-wallet-connect title="POST /wallet/connect" path=backend/wallet.py lines=148:157
@source route-wallet-save title="POST /wallet/documents" path=backend/wallet.py lines=159:169
@source route-wallet-dashboard title="GET /wallet" path=backend/wallet.py lines=177:187
@source route-wallet-retry title="POST /wallet/documents/{id}/retry" path=backend/wallet.py lines=189:193
@source route-wallet-download title="GET /wallet/documents/{id}/file" path=backend/wallet.py lines=206:223
@source route-wallet-proof title="GET /wallet/documents/{id}/proof" path=backend/wallet.py lines=225:229
@source table-datasetrecord title="veris_dataset_records model" path=backend/reference_dataset.py lines=12:23
@source route-reference_dataset-catalogue title="GET /dataset" path=backend/reference_dataset.py lines=50:54
@source route-reference_dataset-test_documents title="GET /dataset/test-documents" path=backend/reference_dataset.py lines=56:58
@source route-reference_dataset-register title="POST /dataset/records" path=backend/reference_dataset.py lines=60:76
@source table-classificationrecord title="veris_classification_records model" path=backend/classification_dataset.py lines=26:35
@source route-classification_dataset-catalogue title="GET /classification/catalogue" path=backend/classification_dataset.py lines=86:103
@source route-classification_dataset-export title="GET /classification/export" path=backend/classification_dataset.py lines=105:120
@source route-classification_dataset-file title="GET /classification/files/{id}" path=backend/classification_dataset.py lines=122:133
@source route-classification_dataset-register title="POST /classification/records" path=backend/classification_dataset.py lines=135:178
@source route-accreditation-submit_claim title="POST /accreditation/claims" path=backend/accreditation.py lines=91:101
@source route-accreditation-review_claim title="POST /accreditation/claims/{id}/reviews" path=backend/accreditation.py lines=110:124
@source route-accreditation-dossiers title="GET /accreditation" path=backend/accreditation.py lines=127:149
@source route-accreditation-check_proof title="GET /ledger/{id}/proof" path=backend/accreditation.py lines=224:233
@source route-accreditation-export_proof title="GET /ledger/{id}/proof-file" path=backend/accreditation.py lines=236:240

## What are the main parts? {#system-map}

@architecture id=system-flow title="Browser, backend and persistence"
| react | React interface | frontend | source:ui |
| proxy | API proxy | cloud | source:proxy |
| api | FastAPI handlers | backend | source:handlers |
| sql | SQL database | database | source:models |
| files | Original files | database | source:upload |
| workers | Background workers | backend | source:lifespan |
| providers | External services | external | source:worker |
| react > proxy | /api request | emphasis |
| proxy > api | strip /api | emphasis |
| api > sql | SQLAlchemy | emphasis |
| api > files | read / write |
| api > workers | enabled loops | dashed |
| workers > sql | persist jobs | dashed |
| workers > files | read originals |
| workers > providers | HTTP / RPC |
| api > providers | consented AI |

@steps id=system-tour
| click-action | React interface | App.tsx owns page state and user actions. Domain panels call the same API helper. | system-flow | react |
| send-request | React interface | api() adds /api, the application header and browser credentials. JSON responses become JavaScript values. | system-flow | react |
| enter-backend | FastAPI handlers | Route functions act as controllers. This code does not have a separate controller class layer. | system-flow | api |
| query-data | FastAPI handlers | Depends(db) creates a request session; handlers issue select(), add(), flush() and commit(). | system-flow | api |
| store-data | SQL database | DATABASE_URL chooses SQLite locally or PostgreSQL through psycopg. Production requires PostgreSQL; Neon is a compatible provider. | system-flow | sql |

The local Vite proxy sends `/api/...` to `http://127.0.0.1:8000/...`. The committed Vercel rewrite instead targets a Railway API URL. These are configured paths, not evidence that either deployment is running.[](source:proxy)[](source:hosted)

`frontend/src/main.tsx` mounts `App`.

Navigation uses the History API and React state; workspace views are selected from the URL. The landing artwork uses lazy Three.js components, Framer Motion and GSAP. Those visuals do not perform evidence assessment.[](source:entry)[](source:ui)

## What happens when I upload evidence? {#upload-journey}

@sequence id=upload-flow title="Upload, saved job and result refresh"
| actor browser | React UI | frontend | source:ui |
| actor server | FastAPI | backend | source:handlers |
| actor disk | Original files | database | source:upload |
| actor db | SQL database | database | source:models |
| actor worker | Verification worker | backend | source:worker |
| actor external | Source providers | external | source:public |
| phase | First request: save the original and queue inspection |
| browser | server | POST /api/documents?background=true | emphasis |
| server | db | current(): account + active session lookup | security |
| server | disk | read_upload() validates; store_file() writes bytes |
| server | db | Add Document + VerificationJob; commit | emphasis |
| server | browser | 201 document_json(): ID + queued job | return |
| phase | Later work: AUTO_VERIFY enables the worker loop |
| worker | db | process_next(): lock and claim queued or stale job | dashed |
| worker | disk | Read original; verify SHA-256; inspect_bytes() |
| worker | db | Save progress stages and intermediate results | dashed |
| worker | external | Conditional DOI/title and official-original checks |
| external | worker | Provider results or explicit unavailable state | return |
| worker | db | run_checks(); save assessment + completed job | emphasis |
| phase | Return path: notify, fetch saved state, render |
| browser | server | EventSource GET /api/events |
| server | db | workspace_revision(): hash visible saved state |
| server | browser | workspace event with revision; or heartbeat | return |
| browser | server | GET /api/workspace and /api/documents/{id} | emphasis |
| server | db | Scoped document / latest job / decision queries |
| server | browser | JSON: verification_response + activity + sources | return |

@steps id=upload-tour
| upload-step | React UI | App.upload() validates file size and sends multipart FormData with file, category and period. | upload-flow | browser |
| receive-step | FastAPI | upload() checks the category and period. read_upload() validates extension, size and PDF header. get_document() later enforces ownership. | upload-flow | server |
| disk-step | Original files | store_file() writes a UUID filename under UPLOAD_DIR. The SQL record stores its storage_name and SHA-256. | upload-flow | disk |
| job-step | SQL database | veris_documents and veris_verification_jobs commit together. If saving fails, rollback removes the new file. | upload-flow | db |
| worker-step | Verification worker | process_next() performs text/OCR, format, signature, type and source checks. It commits progress and the final assessment. | upload-flow | worker |
| provider-step | Source providers | Research documents use DOI or title queries. Supported Nature and NIRF PDFs can receive exact-original byte comparisons. | upload-flow | external |

The sequence shows one source-defined lifecycle, not one long HTTP request. The initial upload returns before full inspection. The later SSE event carries a revision, not the document result; React then fetches the saved JSON.[](source:ui)[](source:workspace)

The worker is a task started by FastAPI lifespan, using a thread for synchronous work. There is no Redis, Celery or separate queue server in this path. `veris_verification_jobs` is the durable work queue. `AUTO_VERIFY=true` enables processing every two seconds; PostgreSQL advisory locks serialize passes, and running jobs older than five minutes can be reclaimed.[](source:lifespan)[](source:worker)

`document_json()` joins the latest job, loads decisions and builds activity history. `verification_response()` produces the displayed assessment. The API helper parses JSON; `setData()` and `setSelectedRecord()` update React, and `EvidenceDetail` and `DocumentAssessment` render it. A 12-second workspace refresh backs up SSE.[](source:serialize)[](source:outcome)[](source:ui)

## How does signing in protect a request? {#authentication}

@sequence id=auth-flow title="Registration, login and protected requests"
| actor browser | Auth form / browser | frontend | source:authui |
| actor api | FastAPI auth | security | source:login |
| actor db | Accounts + sessions | database | source:auth |
| phase | Registration creates an account; then the UI logs in |
| browser | api | POST /api/auth/register: name, institution, credentials |
| api | db | register(): unique email; scrypt hash; add Account |
| api | browser | 201 account; optional invitation grants reviewer role | return |
| browser | api | POST /api/auth/login | emphasis |
| api | db | sign_in(): check_password(); commit AuthSession |
| api | browser | Set-Cookie veris_session; JSON user + token | return |
| phase | Every protected request must pass current() |
| browser | api | Fetch with credentials: include | security |
| api | db | Verify JWT; join account to active, unrevoked session | security |
| db | api | Authorized account or no matching account | return |
| api | browser | Scoped response; invalid sessions return 401 | return |
| phase | Logout invalidates the saved session |
| browser | api | POST /api/auth/logout |
| api | db | Set AuthSession.revoked = 1; commit |
| api | browser | Delete cookie; UI clears user state | return |

Passwords use salted scrypt hashes. JWTs use HS256 and include `sub`, `jti` and an eight-hour expiry. The HttpOnly cookie is Secure in production and SameSite=Lax. The frontend uses the cookie, even though login also returns a token.[](source:auth)[](source:login)[](source:authui)

`guards()` checks POST origins, the `X-Veris-Request: workspace` header for cookie-authenticated writes, request size and an in-memory auth rate limit. CORS has an explicit origin list. `current()` authenticates; `reviewer()` checks the role; `get_document()` checks document ownership. These serve different purposes.[](source:guards)[](source:auth)

Reviewer invitations are hashed, expiring and single-use. Password changes revoke all sessions. There is no external OAuth provider in this authentication path. Institution names are self-declared; official institutional onboarding is not connected.[](source:login)[](source:claims)

## How do wallet signatures become encrypted storage? {#wallet-path}

@sequence id=wallet-flow title="One-use consent, IPFS and the separate vault contract"
| actor ui | Wallet UI | frontend | source:walletui |
| actor wallet | Wallet | external | source:walletconnection |
| actor api | Wallet API | backend | source:challenge |
| actor db | SQL | database | source:walletmodels |
| actor worker | Worker | backend | source:vaultworker |
| actor ipfs | Pinata | cloud | source:walletread |
| actor chain | VerisVault | external | source:vaultcontract |
| phase | Connect or authorize one document save |
| ui | wallet | Choose account; Sepolia if configured |
| ui | api | POST /wallet/challenge: address + optional document_id |
| api | db | Commit expiring WalletChallenge row |
| api | ui | Five-minute, one-use challenge message | return |
| ui | wallet | personal_sign(message, address) | security |
| wallet | ui | EIP-191 signature | return |
| ui | api | POST /wallet/connect or /wallet/documents | emphasis |
| api | db | Consume challenge; commit binding or queued save |
| api | ui | Connected result or 202 queued save | return |
| phase | Enabled worker encrypts, pins and registers the reference |
| worker | db | Read queued veris_wallet_documents via SessionLocal | dashed |
| worker | ipfs | POST encrypted bytes; persist returned CID |
| ipfs | worker | CID for ciphertext | return |
| worker | chain | store(opaque ID, owner, hash, CID, consent hash) |
| chain | worker | Successful matching receipt and stored fields | return |
| worker | db | Commit anchored state, transaction and CID | dashed |
| phase | Authenticated retrieval validates bytes again |
| ui | api | GET /wallet/documents/{id}/file |
| api | db | owned(): check login binding and document ownership |
| api | ipfs | Fetch ciphertext by saved CID |
| ipfs | api | Ciphertext; check hash, decrypt, check original hash | return |
| api | ui | Download original bytes | return |

The API verifies the signature against a locked challenge row and consumes it. Bindings and documents remain scoped to the Veris login, even if the same wallet signs for multiple accounts. Wallet signatures do not replace the application session.[](source:challenge)[](source:walletread)[](source:migrations)

Encryption uses AES-256-GCM with per-document keys derived from a backend master key. Keys remain backend-managed. The user's wallet private key stays in the wallet; the backend relay signs blockchain transactions. Only ciphertext goes to IPFS; the vault stores references and commitments.

Saving a file does not make it genuine.[](source:crypt)[](source:vaultworker)[](source:vaultcontract)

`AUTO_WALLET_STORAGE` controls this worker and falls back to `AUTO_ANCHOR` when unset. The 20-second lifespan loop runs the enabled wallet and fraud-ledger passes. WalletConsole independently polls every seven seconds; wallet records are not part of `workspace_revision()`.[](source:workerflags)[](source:lifespan)[](source:walletui)[](source:workspace)

## What do claims, reviewers and the fraud ledger do? {#claims-audit}

| User action | Backend path and processing | Saved state / return |
| --- | --- | --- |
| Add institutional claim | AccreditationConsole calls POST /accreditation/claims. submit_claim() checks ownership and duplicate claims. | Adds veris_accreditation_claims; returns ID and time, then UI reloads GET /accreditation. |
| Review a claim | POST /accreditation/claims/{id}/reviews calls review_claim(), reviewer() and compare_claim(). | Appends veris_claim_reviews; supported requires an intact, matching issuer original and eligible completed checks. |
| Register issuer original | POST /trusted-records calls source_record(), validates context and stores file bytes. | Adds veris_sources and optional veris_source_metrics; comparisons require a later recheck. |
| Decide document outcome | POST /documents/{id}/decisions calls decide(). Acceptance and appeals require current completed checks and issuer evidence. | Appends veris_decisions and updates veris_documents.status. |
| Confirm fraud or uphold appeal | decide() calls seal_decision() for these two outcomes only. | Adds veris_evidence_snapshots and queued veris_anchors. Other outcomes do not queue ledger records. |
| Run enabled anchor pass | anchor_worker.process() uses Web3 and VerisLedger.anchor(). | Persists signed transaction before broadcast; receipt-backed state and tx_hash return through ledger/workspace reads. |
| Check audit proof | AuditProofPanel calls GET /ledger/{id}/proof. receipt_bundle(), payload_binding() and check_chain() compare snapshot, originals, receipt, event and contract fields. | JSON proof result; /proof-file exports the canonical evidence bundle. |

Evidence: [claim UI](source:claimsui), [claim handlers](source:claims), [comparison gate](source:claimcompare), [source registration](source:trusted), [document decision](source:decisions), [snapshot](source:seal), [anchor worker](source:anchorworker), [ledger contract](source:ledgercontract), [proof endpoints](source:audit), [chain checks](source:chainproof).

`VerisLedger` preserves confirmed findings and linked appeals. `VerisVault` preserves wallet-owned encrypted-file references. They have separate network/contract settings and data models. Both support configured Sepolia or a private development chain; this page does not establish which network is deployed.[](source:anchorworker)[](source:vaultworker)

## Which external services are actually called? {#external-services}

| Service | Actual caller and condition | What returns / where it goes |
| --- | --- | --- |
| Crossref, DataCite, Europe PMC | verification.corroborate() queries primary article DOIs for Research publications. | Metadata records, not-found or unavailable results saved in VerificationJob.result. |
| Crossref and Europe PMC title search | source_discovery.discover_title() when an article title is available without a primary DOI. | Up to three candidates per provider; related papers cannot authenticate uploaded bytes. |
| Nature / Springer Nature hosts | compare_publisher_original() for a supported PDF with one front-page Nature DOI. | Exact SHA-256 comparison; bounded allowlisted downloads. Different bytes alone do not establish fraud. |
| Official NIRF hosts | compare_institutional_original() for identifiable NIRF Overall PDFs. | Report identity and exact-byte match; does not establish ownership or truth of claims. |
| OpenRouter free provider | assist() after explicit consent; requires configured key and a free model. | Up to 12,000 text characters sent; advisory text saved to Document.ai. No review-status write. |
| Pinata upload and gateway | wallet_worker.process() uploads ciphertext; wallet.retrieve() fetches saved CID. | CID, ciphertext hash, decrypted download or explicit errors. |
| Ethereum JSON-RPC | anchor_worker, wallet_worker and proof helpers use Web3. | Contract calls, signed relay transactions and receipt checks. No document contents go on-chain. |
| Browser Ethereum provider | WalletConsole uses EIP-6963 discovery or an injected wallet. | Account choice and personal_sign; private wallet key stays outside the app. |

Evidence: [DOI queries](source:public), [title search](source:search), [publisher comparison](source:publisher), [NIRF comparison](source:nirf), [AI endpoint](source:ai), [wallet upload](source:vaultworker), [IPFS retrieval](source:walletread), [wallet frontend](source:walletui).

PDF parsing, PyMuPDF, pyHanko signatures, Pillow and Tesseract OCR run as backend libraries or local tools. They are not remote verification services. Document classification is a versioned content-rule baseline with curated exact-type references; it is not a trained fraud model.[](source:inspect)[](source:classify)

## Where does the application keep data? {#data-model}

`create_engine(DATABASE_URL)` creates the connection pool; `SessionLocal` creates units of database work. `Base.metadata.create_all(engine)` creates known tables at startup. A targeted migration removes legacy global wallet-address uniqueness. There is no general Alembic migration framework in this startup path.[](source:db)[](source:lifespan)[](source:migrations)

The tables below use SQL string IDs for logical joins. These ORM models do not declare SQL ForeignKey constraints or ORM relationships. The links shown are application-enforced queries, not database-enforced foreign keys. JSON payloads such as checks, job results and annotations are stored in Text columns.[](source:models)[](source:walletmodels)[](source:classrecords)

| SQL table | Purpose and logical links | Physical columns | Evidence |
| --- | --- | --- | --- |
| `veris_accounts` | Login identity, salted password hash and institution role. | `id`, `email`, `password`, `name`, `college`, `role` | [Model](source:table-account) |
| `veris_documents` | Evidence metadata and extracted text; owner_id joins Account.id; storage_name points to disk. | `id`, `owner_id`, `filename`, `college`, `category`, `period`, `sha256`, `storage_name`, `status`, `created_at`, `text`, `checks`, `ai` | [Model](source:table-document) |
| `veris_decisions` | Append-only reviewer decision; document_id joins Document.id. | `id`, `document_id`, `reviewer_id`, `reviewer`, `outcome`, `reason`, `evidence`, `created_at` | [Model](source:table-decision) |
| `veris_sources` | Registered issuer original and context; points to disk. | `id`, `sha256`, `college`, `category`, `period`, `issuer`, `reference`, `reviewer_id`, `storage_name` | [Model](source:table-sourcerecord) |
| `veris_anchors` | Fraud/appeal ledger queue; case_id is Document.id; id is Decision.id. | `id`, `case_id`, `document_hash`, `evidence_hash`, `outcome`, `timestamp`, `parent_id`, `state`, `tx_hash`, `raw_transaction` | [Model](source:table-anchor) |
| `veris_source_metrics` | Issuer quantity; source_id joins SourceRecord.id. | `id`, `source_id`, `name`, `value` | [Model](source:table-sourcemetric) |
| `veris_network_config` | Configured or deployed chain contract and start block. | `network`, `address`, `start_block` | [Model](source:table-networkconfig) |
| `veris_auth_sessions` | Revocable login session; user_id joins Account.id. | `id`, `user_id`, `expires`, `revoked` | [Model](source:table-authsession) |
| `veris_reviewer_invites` | Hashed one-use reviewer invitation. | `digest`, `expires`, `claimed_by` | [Model](source:table-reviewerinvite) |
| `veris_archived_records` | Exclusion registry for archived IDs; filters visibility. | `id`, `kind`, `reason`, `created_at` | [Model](source:table-archive) |
| `veris_verification_jobs` | Durable queue and progress; document_id joins Document.id; result stores source/assessment JSON. | `id`, `document_id`, `state`, `stage`, `progress`, `created_at`, `updated_at`, `result`, `error`, `timeline` | [Model](source:table-verificationjob) |
| `veris_accreditation_claims` | Institution claim; document_id and owner_id link evidence and submitter. | `id`, `document_id`, `owner_id`, `criterion`, `statement`, `issuer`, `quantity`, `created_at` | [Model](source:table-accreditationclaim) |
| `veris_claim_reviews` | Review history; claim_id joins AccreditationClaim.id. | `id`, `claim_id`, `reviewer_id`, `reviewer`, `outcome`, `reason`, `evidence`, `created_at` | [Model](source:table-claimreview) |
| `veris_evidence_snapshots` | Canonical review-time evidence; id matches decision/anchor; document_id links evidence. | `id`, `document_id`, `payload`, `digest`, `created_at` | [Model](source:table-evidencesnapshot) |
| `veris_wallet_bindings` | One row per application user; wallet address can serve multiple users. | `user_id`, `address`, `connected_at` | [Model](source:table-walletbinding) |
| `veris_wallet_challenges` | Expiring one-use signed message scoped to login and optional document. | `id`, `user_id`, `address`, `document_id`, `message`, `expires`, `consumed` | [Model](source:table-walletchallenge) |
| `veris_wallet_documents` | Save queue, consent, CID and receipt; document_id is primary key. | `document_id`, `user_id`, `address`, `sha256`, `consent`, `signature`, `network`, `state`, `cid`, `ciphertext_sha256`, `tx_hash`, `raw_transaction`, `contract_address`, `error`, `created_at`, `updated_at` | [Model](source:table-walletdocument) |
| `veris_dataset_records` | Reviewer-registered exact-file authenticity reference with institutional context. | `id`, `sha256`, `label`, `college`, `category`, `period`, `reference`, `storage_name`, `reviewer_id`, `created_at` | [Model](source:table-datasetrecord) |
| `veris_classification_records` | Unique-file type annotation; JSON provenance, family and split; not an authenticity authority. | `id`, `sha256`, `filename`, `storage_name`, `annotation`, `reviewer_id`, `created_at` | [Model](source:table-classificationrecord) |

The filesystem stores original uploads, registered issuer/reference files and staged encrypted `.vault` files. `storage_name` locates bytes; `sha256` identifies them. The bundled dataset manifests, classification labels and test ZIP live under `backend/datasets/`, separate from user SQL rows. There is no MongoDB collection in these paths.[](source:upload)[](source:vaultworker)[](source:dataset)[](source:classrecords)

## Which API routes exist, and who receives each one? {#api-catalogue}

These are all explicit application GET/POST routes registered by `main.py` and its four imported routers. FastAPI's generated documentation routes are outside this catalog. Browser calls add `/api`; the proxy removes that prefix. A declared route is not necessarily used by the current interface.[](source:proxy)[](source:transport)

| Backend route | Receiving function | Access dependency | Evidence |
| --- | --- | --- | --- |
| `GET /health` | `main.py:health()` | Public | [Handler](source:route-main-health) |
| `POST /auth/register` | `main.py:register()` | Public | [Handler](source:route-main-register) |
| `POST /auth/login` | `main.py:sign_in()` | Public | [Handler](source:route-main-sign_in) |
| `GET /auth/me` | `main.py:me()` | Signed-in account | [Handler](source:route-main-me) |
| `POST /auth/logout` | `main.py:logout()` | Signed-in account | [Handler](source:route-main-logout) |
| `POST /auth/password` | `main.py:change_password()` | Signed-in account | [Handler](source:route-main-change_password) |
| `GET /documents` | `main.py:list_documents()` | Signed-in account | [Handler](source:route-main-list_documents) |
| `POST /documents` | `main.py:upload()` | Signed-in account | [Handler](source:route-main-upload) |
| `GET /documents/{id}` | `main.py:detail()` | Signed-in account | [Handler](source:route-main-detail) |
| `GET /documents/{id}/file` | `main.py:original()` | Signed-in account | [Handler](source:route-main-original) |
| `POST /documents/{id}/recheck` | `main.py:recheck()` | Signed-in account | [Handler](source:route-main-recheck) |
| `POST /documents/{id}/verify` | `main.py:enqueue_verification()` | Signed-in account | [Handler](source:route-main-enqueue_verification) |
| `POST /trusted-records` | `main.py:source_record()` | Reviewer | [Handler](source:route-main-source_record) |
| `POST /documents/{id}/decisions` | `main.py:decide()` | Reviewer | [Handler](source:route-main-decide) |
| `POST /documents/{id}/ai` | `main.py:assist()` | Signed-in account | [Handler](source:route-main-assist) |
| `GET /ledger` | `main.py:ledger()` | Signed-in account | [Handler](source:route-main-ledger) |
| `GET /documents/{id}/report` | `main.py:evidence_report()` | Signed-in account | [Handler](source:route-main-evidence_report) |
| `GET /workspace` | `main.py:workspace()` | Signed-in account | [Handler](source:route-main-workspace) |
| `GET /events` | `main.py:events()` | Signed-in account | [Handler](source:route-main-events) |
| `GET /trusted-records/{id}/file` | `main.py:source_file()` | Reviewer | [Handler](source:route-main-source_file) |
| `POST /wallet/challenge` | `wallet.py:challenge()` | Signed-in account | [Handler](source:route-wallet-challenge) |
| `POST /wallet/connect` | `wallet.py:connect()` | Signed-in account | [Handler](source:route-wallet-connect) |
| `POST /wallet/documents` | `wallet.py:save()` | Signed-in account | [Handler](source:route-wallet-save) |
| `GET /wallet` | `wallet.py:dashboard()` | Signed-in account | [Handler](source:route-wallet-dashboard) |
| `POST /wallet/documents/{id}/retry` | `wallet.py:retry()` | Signed-in account | [Handler](source:route-wallet-retry) |
| `GET /wallet/documents/{id}/file` | `wallet.py:download()` | Signed-in account | [Handler](source:route-wallet-download) |
| `GET /wallet/documents/{id}/proof` | `wallet.py:proof()` | Signed-in account | [Handler](source:route-wallet-proof) |
| `GET /dataset` | `reference_dataset.py:catalogue()` | Signed-in account | [Handler](source:route-reference_dataset-catalogue) |
| `GET /dataset/test-documents` | `reference_dataset.py:test_documents()` | Signed-in account | [Handler](source:route-reference_dataset-test_documents) |
| `POST /dataset/records` | `reference_dataset.py:register()` | Reviewer | [Handler](source:route-reference_dataset-register) |
| `GET /classification/catalogue` | `classification_dataset.py:catalogue()` | Signed-in account | [Handler](source:route-classification_dataset-catalogue) |
| `GET /classification/export` | `classification_dataset.py:export()` | Signed-in account | [Handler](source:route-classification_dataset-export) |
| `GET /classification/files/{id}` | `classification_dataset.py:file()` | Signed-in account | [Handler](source:route-classification_dataset-file) |
| `POST /classification/records` | `classification_dataset.py:register()` | Reviewer | [Handler](source:route-classification_dataset-register) |
| `POST /accreditation/claims` | `accreditation.py:submit_claim()` | Signed-in account | [Handler](source:route-accreditation-submit_claim) |
| `POST /accreditation/claims/{id}/reviews` | `accreditation.py:review_claim()` | Reviewer | [Handler](source:route-accreditation-review_claim) |
| `GET /accreditation` | `accreditation.py:dossiers()` | Signed-in account | [Handler](source:route-accreditation-dossiers) |
| `GET /ledger/{id}/proof` | `accreditation.py:check_proof()` | Signed-in account | [Handler](source:route-accreditation-check_proof) |
| `GET /ledger/{id}/proof-file` | `accreditation.py:export_proof()` | Signed-in account | [Handler](source:route-accreditation-export_proof) |

## What should I remember when reading this code? {#reading-guide}

| Concept | Plain-language meaning in Veris | Where to start |
| --- | --- | --- |
| Frontend state | React keeps the current user, selected page, modal and returned JSON in memory. | App.tsx:34–59; API helper:1–8. |
| Controller | A FastAPI route function receives validated input and coordinates permissions, work and persistence. | main.py upload(), decide(), workspace(); imported router modules. |
| Service | Python functions perform checks, source discovery, claims comparison or wallet/chain operations. | verification.process_next(), authenticity.assessment(), accreditation.compare_claim(), wallet_worker.process(). |
| Database session | A short-lived SQLAlchemy object reads and stages SQL changes; commit() makes them durable. | main.py:42–44,182–183; worker sessions. |
| Background queue | A persisted SQL row waits for an enabled worker pass. Queueing success is different from completion. | veris_verification_jobs, veris_wallet_documents, veris_anchors. |
| Response | Handlers return dictionaries or file bytes; the frontend parses JSON or downloads a Blob. | document_json(), verification_response(), api(), downloadFile(). |
| Evidence scope | A Genuine file assessment does not support every institutional claim; AI advice and blockchain storage do not establish authenticity. | authenticity.py:201–214; document_response.py:5–76. |

Evidence: [entry and UI](source:ui), [database session](source:db), [response builder](source:serialize), [assessment rules](source:rules), [file/JSON client](source:transport).

This is a static analysis of committed code at `e27a6ed7cd2c57bd769065985c790bdb926497fe`, not a capture of live requests, database contents, production configuration or service availability. The page contains no credentials and makes no application API calls. Source links target that exact commit. Worker intervals come from code; no runtime timings were measured.
