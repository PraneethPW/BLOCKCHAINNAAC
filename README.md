# Veris — Connected accreditation evidence

Independent working prototype. No NAAC affiliation; no accreditation grades.

For installation and startup instructions, see [Local development](#local-development).

## Experience

React + TypeScript + Tailwind, Framer Motion, Three.js / React Three Fiber and GSAP ScrollTrigger. The landing uses a persistent WebGL environment: custom architectural textures blend with scroll position, flowing light filaments, small glints, ambient camera movement and a fine-pointer depth response. A consistent navy, blue and cyan palette connects it to the authenticated product. The compact product layout includes an interactive, keyboard-accessible workflow illustration; it never fabricates a document assessment. The previous header journey link and pause control are removed. Device or saved reduced-motion preferences render a static poster and remove ambient animation. The shader loads separately, caps rendering resolution and stops while the tab is hidden; unsupported WebGL retains the poster. Authentication and the workspace retain their existing background and functionality. Keyboard navigation, modal focus containment and responsive layouts are included. There are no runtime sample users, seeded dashboards or fabricated verification responses. Image provenance and generation prompts are recorded in frontend/public/images/ASSET_NOTES.md.

## Authentication and access

Institution registration, login, logout and password changes use scrypt password hashes and eight-hour HttpOnly sessions. Production cookies are Secure and SameSite=Lax. JWT session IDs are stored in PostgreSQL and checked on requests; logout revokes the current session and password changes revoke all sessions. State-changing cookie requests require an application header and allowed Origin. Ownership checks protect files, reports, decisions and ledger visibility. Reviewer access requires a hashed, expiring, single-use invitation or authorized backend provisioning.

Use your own account. Issue a private reviewer invitation from an authorized backend shell with python provision_invitation.py --days 7. Do not publish invitation codes. No reviewer role selector is available to public users. Institution identity is self-entered until an authorized onboarding process is connected; email ownership verification and recovery email are not configured.

## Accreditation cases and institutional claims

The workspace starts with actual institutional reporting cases, grouped by submitting account and period. Each immutable claim declares its criterion reference, statement, expected issuer and supporting document. Criterion references are supplied by the institution; the prototype does not embed an official NAAC assessment framework. Existing uploads appear as evidence without inventing claims for them.

Student placement quantities are compared across the institution's stated count, readable document text and reviewer-registered evidence from the declared issuer in the same institution/category/period. Missing, ambiguous, changed or conflicting issuer evidence cannot support a claim. Other claim types use original-file corroboration and substantive human review; there is no universal semantic authenticity classifier. A supported claim requires a verified original, a completed current-engine job, intact exact issuer evidence and agreement on any structured count. Review outcomes and reasons append to claim history. Insufficient evidence or clarification requests do not establish fraud or create blockchain findings.

GET /accreditation returns only visible cases. Institution accounts submit claims using POST /accreditation/claims. Invited reviewers append decisions using POST /accreditation/claims/{id}/reviews. Claims have no editing or deletion endpoint. Workspace SSE revisions include actual claim submissions and review events.

## Verification

Engine 3.4 retains up to 8,000 characters of first-page text for title consistency, including layouts that extract affiliations before the heading. Correction notices distinguish their own DOI from the "Correction to" relation. A correction's editable DOI metadata can select a publisher query, but only an exact independently retrieved publisher PDF match authenticates the file; a borrowed identifier or changed bytes cannot pass.

Uploaded originals receive an exact SHA-256 fingerprint and a durable database job. A background worker records committed stages, timestamps, errors and provider results. PostgreSQL advisory locking serializes worker passes and interrupted jobs are retried after five minutes. Stored bytes are rehashed before processing; an integrity mismatch stops verification while retaining evidence.

The worker extracts bounded native PDF text, runs Tesseract OCR on images and up to twelve scanned PDF pages, inspects PDF metadata, signature fields and active actions, detects duplicate fingerprints and repeated normalized text in the same institutional context. Reviewer-registered issuer records support exact-file comparisons and placement counts for matching institution/category/period. Originals are authenticated downloads, never executed inside the app.

Engine 3.1 scopes article claims to front-matter DOI identifiers (up to eight per pass). Bibliography DOIs are recorded separately and excluded from article authentication. Crossref, DataCite and Europe PMC responses retain identifier, endpoint, time, metadata and found/not-found/unavailable state. When no article DOI is available, the extracted PDF title or inferred first-page heading is queried against Crossref and Europe PMC. Each bounded title search returns up to three candidates, explicitly labeled as same-title or related records; neither authenticates the uploaded bytes. Exact-title absence refers only to the returned candidates, not every publication on the internet. Queries, provider errors, zero-result responses, elapsed times and endpoints are saved as each provider finishes. Crossref uses its supported query.bibliographic parameter. Registry titles are compared with the cover/front matter, not the entire bibliography. Editable title metadata, observed author surnames and front-matter years are consistency observations, not proof of authorship. Only fixed registry hosts are contacted; uploaded URLs are never fetched. Missing records and provider outages never establish fraud.

Cover and metadata declarations such as educational sample, not a published article and layout demonstration create blocking review findings. PDFs receive strict structural checks and offline embedded-signature byte validation through pyHanko. Ordinary page-opening destinations are not classified as executable actions. Signed-byte integrity remains separate from certificate identity, trust and revocation, which are not configured. Uploaded certificate URLs are never fetched. Multiple PDF revisions alone do not establish manipulation.

The dashboard separates authenticity from processing completion. A readable PDF, new fingerprint or real cited publication cannot establish authenticity. Automatic genuine-file results and manually upheld appeals require a completed current-engine job, an exact reviewer-registered issuer file for the same institution/category/period, intact stored originals and issuer files, and no blocking conflicts. A written evidence reference by itself cannot bypass this gate. Reviewer registration remains a human attestation of issuer provenance; there is no automatic issuer integration. Re-run earlier documents to obtain the new assessment; legacy results do not grant acceptance.

Engine 3.3 produces an automatic document assessment, saved with each verification run and displayed consistently in the evidence library, accreditation case, result view, activity history and PDF report. Results include Genuine — matches registered issuer original, Manipulated — stored file changed, Corrupted — invalid file structure, Non-original — sample document, Fake / fabricated — declared fictional document, Conflicting evidence, and Neutral. Neutral is a completed assessment with no decisive authenticity evidence; it is not a pending human review. Parser-proven PDF/image format failures are distinguished from encrypted files, unsupported encoding, inspection limits and service failures. Exact intact registered issuer files and completed current checks without conflicts can automatically mark a file verified. This is scoped to that source comparison and does not establish institutional ownership or accreditation claims. Public metadata matches, absent signatures and provider errors do not produce guessed genuine/fake verdicts. Human review remains available for institutional claims, fraud adjudication and appeals; historical decisions and blockchain snapshots are preserved. Recheck older files to save a current automatic assessment.

SSE events announce actual workspace changes, including persisted provider responses, with authenticated reconnects and a periodic refresh fallback. Search and status filters query PostgreSQL and the library paginates all matching records. The result view leads with the observed conflict and next step; technical checks and AI assistance use expandable sections. Document detail requests include the original upload, latest twenty verification runs and all human decisions. Activity and decisions are explicitly distinguished, with durable timestamps and reviewer reasons. The modal uses the full document response rather than overwriting it with the library summary. PDF reports include search attempts, check results, source provenance, activity, decisions, transaction hashes and optional advisory notes. Existing submissions need a fresh recheck to add title searches; no placeholder sources or decisions are inserted.

OpenRouter assistance requires explicit document consent, sends at most 12,000 extracted characters, denies provider data collection and uses only a :free model or openrouter/free. AI returns investigation advice and never changes review status. Capacity or privacy-policy failures appear as errors; no paid or fabricated fallback is used.

Only supported authorized decisions establish verified or confirmed-fraud status. Confirmed findings and upheld appeals create append-only blockchain records containing opaque IDs and hashes. Sensitive files and narratives remain off-chain. Appeals preserve the earlier finding. Anchored status requires an actual successful transaction receipt.

## Local development

### 1. Install prerequisites

Install **Git**, **Node.js 22 or later**, and **Python 3.12**. The commands below use **Windows PowerShell**. Install pnpm 10 using npm, which comes with Node.js:

```powershell
git --version
node --version
py -3.12 --version
npm install --global pnpm@10
pnpm --version
```

For scanned PDFs and image uploads, also install **Tesseract OCR** and add its executable directory to `PATH`. Confirm `tesseract --version` works in a newly opened terminal. Native PDF text extraction works without Tesseract; unreadable scans cannot obtain OCR text until it is installed. The Railway Docker image already includes Tesseract.

### 2. Clone the project and install backend dependencies

```powershell
git clone https://github.com/PraneethPW/BLOCKCHAINNAAC.git
cd BLOCKCHAINNAAC
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The commands use the virtual environment's Python directly, so PowerShell activation or execution-policy changes are unnecessary.

### 3. Create the local backend configuration

While inside `backend`, run this block **once for a new local installation**. It creates `backend/.env` with a random session secret and a local SQLite database. If `.env` already exists, edit it instead of replacing it or generating a new vault encryption key.

```powershell
$verisLocalSecret = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
@"
APP_ENV=development
DATABASE_URL=sqlite:///./veris.db
JWT_SECRET=$verisLocalSecret
FRONTEND_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
UPLOAD_DIR=./uploads
AUTO_VERIFY=true
AUTO_ANCHOR=false
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free
LEDGER_NETWORK=sepolia
SEPOLIA_RPC_URL=
LEDGER_CONTRACT_ADDRESS=
LEDGER_PRIVATE_KEY=
VAULT_NETWORK=sepolia
VAULT_SEPOLIA_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
VAULT_PRIVATE_KEY=
VAULT_CONTRACT_ADDRESS=
PINATA_JWT=
VAULT_ENCRYPTION_KEY=
"@ | Set-Content -Encoding ascii .env
```

Do not use the Railway-oriented defaults in `backend/.env.example` unchanged: `APP_ENV=production` requires PostgreSQL, and `/data/uploads` is the hosted volume path. The local settings above use `development`, `./uploads` and SQLite. Configuration is loaded by the `--env-file .env` startup argument; merely creating the file does not configure other Python commands. Existing process environment variables take precedence over the file.

**Optional Neon database:** replace only `DATABASE_URL` with the PostgreSQL connection string from a separate Neon development database, including its SSL parameters. For example:

```dotenv
DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@YOUR_NEON_HOST/YOUR_DATABASE?sslmode=require
```

Use your own values, not the example placeholders. Startup creates the application's tables automatically. No manual SQL import or dataset import is needed. A local SQLite installation is separate from the hosted application's users and documents; using the production Neon URL would connect to production records.

### 4. Start the backend — terminal 1

Keep this terminal open, with its working directory set to `BLOCKCHAINNAAC/backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --env-file .env --host 127.0.0.1 --port 8000 --reload
```

Check [API health](http://127.0.0.1:8000/health): it should return `"status":"ok"` and, with the default local configuration, `"database":"local-sqlite"`. Interactive API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). `AUTO_VERIFY=true` runs the document-processing worker inside this server.

### 5. Install and start the frontend — terminal 2

Open a second terminal at the cloned `BLOCKCHAINNAAC` folder:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1 --port 5173 --strictPort
```

Open **[http://127.0.0.1:5173](http://127.0.0.1:5173)**. The frontend sends requests to same-origin `/api`; Vite forwards them to the **local backend on port 8000**. It does not use the hosted Railway API during local development. No frontend `.env` or frontend secret is required. Keep both terminals running; press `Ctrl+C` in each terminal to stop the application.

### 6. Register and check a document

1. Select **Create an account**, enter your institution details, and choose a password of at least **12 characters**. There are no default accounts or sample passwords.
2. Open **Dataset references** to inspect category coverage, download originals and export CSV/JSON labels. The repository already includes the reference PDFs and manifests in `backend/datasets/`.
3. Select **Upload evidence** and use a matching category. For a source-comparison check, upload the unchanged `GPA_Environment_Lab_Inventory.pdf` under **Infrastructure**. After automatic processing, it should show **Genuine — matches reference dataset original** and **Laboratory inventory**. This result establishes file provenance, not ownership by your institution.
4. Original uploads are saved in `backend/uploads/`; local database records are saved in `backend/veris.db` when SQLite is selected. Files enter Pinata only through a separately configured and authorized wallet save.

To create a reviewer invitation for this local instance, run the following from `backend` in a separate terminal, then use the returned private invitation during registration:

```powershell
.\.venv\Scripts\python.exe -m dotenv -f .env run -- .\.venv\Scripts\python.exe provision_invitation.py --days 7
```

### Optional AI and Sepolia wallet setup

Document upload, classification, reference comparisons and reports work without OpenRouter, Pinata or a funded blockchain wallet. Features that require an external provider need their actual configuration:

| Feature | Backend `.env` settings / requirements |
| --- | --- |
| AI advisory analysis | Set `OPENROUTER_API_KEY`; keep `OPENROUTER_MODEL=openrouter/free` or an available `:free` model. Users must consent before document text is sent. |
| MetaMask connection | Install/unlock MetaMask in the browser used for the local app, select Sepolia, then use **Document wallet → Connect & sign**. Wallet connection alone does not upload files to IPFS. |
| Encrypted Pinata/IPFS saves and Sepolia records | Set `PINATA_JWT`, `VAULT_ENCRYPTION_KEY`, `VAULT_SEPOLIA_RPC_URL`, `VAULT_PRIVATE_KEY`, and the actual `VAULT_CONTRACT_ADDRESS`; enable `AUTO_ANCHOR=true` after configuration. The contract's writer must match the backend relay key, and that relay needs Sepolia test ETH. |
| Fraud audit anchoring | Configure the independent `LEDGER_NETWORK`, corresponding RPC URL, `LEDGER_PRIVATE_KEY` and deployed ledger contract. The fraud ledger and document vault are separate contracts; configuring one does not configure the other. |

Generate a **new** vault encryption key only when configuring a new vault, and retain it for future document retrieval:

```powershell
.\.venv\Scripts\python.exe -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

Put the output in `VAULT_ENCRYPTION_KEY`. For a new Sepolia vault, follow the **Signed document wallet and encrypted IPFS vault** section below. Its deployment script also needs the `.env` values loaded; for example, from `backend`:

```powershell
.\.venv\Scripts\python.exe -m dotenv -f .env run -- .\.venv\Scripts\python.exe deploy_vault.py --journal ..\..\veris-private\vault-deployment.json
```

The journal path above creates `veris-private` alongside the cloned repository, outside Git's working tree. Set `VAULT_CONTRACT_ADDRESS` to the address returned by your own deployment, then restart the backend. Keep deployment journals, keys and `.env` private. Never put database passwords, OpenRouter keys, Pinata tokens, wallet private keys or recovery phrases in frontend variables or commit them to Git. `AUTO_ANCHOR=false` in the basic setup intentionally leaves blockchain writes disabled; it does not create simulated receipts.

### macOS / Linux equivalents

Use the same configuration values from step 3 in `backend/.env`. Generate `JWT_SECRET` with `python -c "import secrets; print(secrets.token_hex(32))"` after activating the environment, and paste that output as its value instead of the PowerShell variable `$verisLocalSecret`. Backend commands:

```bash
git clone https://github.com/PraneethPW/BLOCKCHAINNAAC.git
cd BLOCKCHAINNAAC/backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# Create .env using step 3's settings before starting the server.
python -m uvicorn main:app --env-file .env --host 127.0.0.1 --port 8000 --reload
```

In another terminal, enter `BLOCKCHAINNAAC/frontend`, run `npm install --global pnpm@10`, then `pnpm install --frozen-lockfile` and `pnpm dev --host 127.0.0.1 --port 5173 --strictPort`. For optional backend utility commands, the activated environment supports `python -m dotenv -f .env run -- python provision_invitation.py --days 7` and the equivalent vault deployment command.

### Common local setup problems

| Symptom | Check / fix |
| --- | --- |
| `py -3.12`, `node`, or `pnpm` not found | Install the corresponding prerequisite and reopen the terminal so `PATH` updates take effect. |
| Backend says production requires PostgreSQL | Confirm `APP_ENV=development` in the local `.env` and remove any conflicting `APP_ENV` exported by your terminal. |
| Frontend shows `/api` connection errors | Start the backend on `127.0.0.1:8000` and check `/health`; the frontend must run on port 5173. |
| Port already in use | Stop the earlier local server using that port. The documented frontend command fails instead of silently moving to an origin absent from `FRONTEND_ORIGINS`. |
| Verification remains queued | Check `AUTO_VERIFY=true`, restart the backend after configuration changes, and inspect its terminal for worker errors. |
| OCR unavailable | Confirm `tesseract --version` succeeds in the same environment used to start the backend. |
| Hosted login does not work locally | Register a local account when using SQLite; hosted and local databases are separate. Use one frontend address consistently (`127.0.0.1` or `localhost`), since browser sessions belong to that origin. |
| Wallet save unavailable or stays queued | Complete the Pinata, encryption, RPC, contract and funded-relay configuration; enable `AUTO_ANCHOR` and restart. MetaMask connection does not supply the backend relay credentials. |

### Local validation commands

From `backend`, run the isolated regression suite or replay the classification corpus:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe evaluate_classification.py --output classification-evaluation.json
```

From `frontend`, run `pnpm build` to check TypeScript and generate `dist/`. The classification replay is a development diagnostic, not a held-out accuracy benchmark. Production hosting uses `frontend/vercel.json` to proxy `/api` to Railway; see the hosting section for that separate configuration.

## Hosting

Vercel: import PraneethPW/BLOCKCHAINNAAC, root frontend, framework Vite, build pnpm build, output dist. Update the proxy destination if the backend domain changes. Add the exact frontend HTTPS origin to Railway FRONTEND_ORIGINS.

Railway API: root /backend, Dockerfile, healthcheck /health, PORT supplied by Railway. Mount /data and set UPLOAD_DIR=/data/uploads. Set DATABASE_URL, JWT_SECRET (32+ random characters), APP_ENV=production, FRONTEND_ORIGINS, AUTO_VERIFY=true, OPENROUTER_API_KEY and OPENROUTER_MODEL. The hosted free model is dots-studio/dots-3-note-preview:free; availability can change.

Tables use the veris_ prefix. Startup creates missing tables without changing unrelated data. Archive rows hide prior QA records and deny archived account access without deleting evidence or blockchain history. Future schema changes require migrations.

## Blockchain

The current hosted network is private Ganache, chain ID 1337, accessible only over Railway private networking. Its persistent /data volume retains history. LEDGER_NETWORK=private-devnet, LEDGER_RPC_URL, LEDGER_PRIVATE_KEY and AUTO_ANCHOR=true configure anchoring. The deployed contract address is retained in Neon; missing contract code stops writes rather than resetting history. Signed transactions are persisted before broadcast and advisory locking prevents concurrent worker passes.

This network produces real Ethereum receipts but is centrally operated development infrastructure. Independent validator governance, key custody, finality policy and backups are needed for a consortium deployment. Sepolia remains supported via LEDGER_NETWORK=sepolia, SEPOLIA_RPC_URL, LEDGER_CONTRACT_ADDRESS and a funded test wallet. Never switch an existing ledger database between networks without a migration.

Contract commands in contracts: pnpm install, pnpm compile, node test.mjs. Backend anchoring: python anchor_worker.py. The contract restricts writers, prevents duplicate IDs and validates appeal linkage. It has no record update or delete path.

New confirmed findings and upheld appeals create a canonical, private review-time snapshot of the institution, period, original fingerprint, claim declarations/reviews, verification results and provider responses, registered issuer records/counts, and reviewer decision. The snapshot SHA-256 becomes the contract's evidenceHash; private fields are not put on-chain. The snapshot, decision and queued anchor are committed atomically. Older records preserve their original decision-narrative digest and are explicitly labeled as legacy; historical evidence is never reconstructed as if it had been sealed.

The audit trail's Check receipt & evidence action rehashes current originals, issuer evidence and the stored snapshot, checks preserved institutional/claim/decision context, and reads the actual RPC chain, receipt, canonical block, emitted event and contract record. A changed database row, unrelated successful receipt or changed evidence cannot produce a positive audit match. A valid audit proves consistency with the sealed review evidence; it does not prove the review was correct. An unavailable RPC or pending transaction is displayed without inferring a match.

Export audit proof downloads an authenticated JSON bundle with the exact canonical snapshot and expected contract fields. A separate verifier can use python backend/verify_receipt.py proof.json --rpc YOUR_NETWORK_RPC --document ORIGINAL. This requires no application credentials or wallet, submits no transaction, and hashes the local file without uploading it. The verifier binds exported fields to the snapshot rather than trusting the bundle's status flags. Keep exported snapshots private because they contain authorized review evidence. Independent verification of the hosted private network requires an authorized read endpoint; no public RPC is exposed by the prototype.

## Validation

Frontend: pnpm build. Backend: python -m pytest tests -q. Tests use isolated temporary databases and provider test doubles only within tests; they are not runtime fallbacks. Tests cover isolation, review authorization, append-only appeals, issuer counts, file validation, AI consent/free-model rules, cookie CSRF, logout/password revocation, invitation reuse, durable jobs, tamper detection, archival and server-side pagination/search. Authenticity regressions cover citation-only samples, borrowed DOI/title mismatches, unavailable providers, issuer evidence gates, changed issuer files, corrupt structure, harmless PDF destinations, and actual signed-byte validation with a self-signed ephemeral test certificate. Changed signed bytes fail; a self-signed signer is never reported as authenticated.

Accreditation regressions additionally cover claim count/issuer acceptance gates, owner isolation, immutable claim submission, append-only claim review, changed issuer originals after support, sealed snapshots, legacy receipt scope, and post-sealing changes to claims, decisions, period, issuer counts and originals. A separate isolated Ganache integration verifies real receipts and exported proofs and rejects changed snapshots, changed originals and unrelated successful receipts. No test account, fabricated claim or fraud finding is inserted into production.

A live local integration pass queried a publication DOI: Crossref and Europe PMC returned records, DataCite returned not-found, and review status remained unverified. OpenRouter returned real advisory text without changing status. Browser QA covers 375px phone, 768px tablet, 1440px desktop and short landscape navigation, cookie restoration, source views, motion controls and logout.

## Boundaries and operational work

Public scholarly APIs cannot authenticate placement letters, financial statements, certificates or institutional ownership without issuer access. Signed-byte integrity is checked, but cryptographic signer-chain/revocation validation is not configured. Extraction and OCR have explicit resource bounds. Login throttling is per process. Session rows and jobs are durable; deployment-scale rate limiting, malware scanning, email verification/recovery, encryption and retention policies, backups, immutable off-chain storage and independent validator governance remain operational work. This is a working independent prototype, not certified production accreditation infrastructure.

Supported Nature research PDFs can now authenticate through an independently downloaded official publisher original. A single front-page DOI generates the publisher URL; user-supplied URLs and bibliography identifiers are never used. HTTPS redirects stay inside an explicit publisher host allowlist, downloads and time are bounded, and the official PDF must carry the same front-page DOI. Only an exact byte fingerprint match grants an automatic Genuine — matches publisher original result. The source URL, both fingerprints and comparison time are retained in each run, public sources and PDF reports. Different bytes can represent a legitimate manuscript or re-export and do not automatically establish fabrication. Publisher file authentication never establishes institutional authorship or replaces context-matched issuer evidence for accreditation claim support. Provider failures remain neutral.


### Engine 3.5: official institutional originals

Identifiable NIRF Overall PDF reports now support automatic **Genuine — matches official institutional original** results across upload categories. First-page report identity selects a canonical NIRF URL; only an exact SHA-256 comparison with a freshly fetched official PDF authenticates the file. Source report year and institution ID must agree. HTTPS hosts, redirects, download size, page count and time are bounded. Uploaded URLs are never fetched. Both hashes, the official institution, source URL and comparison timestamp appear in Public sources and the PDF report.

This verifies a whole report file, not its self-reported claims, every category-specific claim, or another college's ownership. Missing sources, excerpts and re-exported PDFs remain Neutral; byte differences alone are not fraud. Existing integrity, fictional-document and conflicting-evidence checks still block acceptance. Controlled training references are not registered automatically. Existing uploads require Recheck now for engine 3.5.

### Engine 3.6: document reference dataset

Dataset references exposes versioned exact-file reference records and an authenticated download of 20 test PDFs: eight unchanged public issuer/publisher originals, six explicitly fabricated fixtures and six partial-evidence Neutral fixtures. Each reference includes its SHA-256, source, scope and expected label. The supplied hospital dataset (50 insurance claims) is not used as document-authenticity training data. No custom classifier was trained and unknown documents do not acquire invented labels.

An exact intact dataset original can support an automatic Genuine file result, subject to the existing blocking checks. Known fabricated fixtures produce a Fake / fabricated result; that test label is not a confirmed institutional fraud decision. Invited reviewers can register context-specific document references with provenance evidence. Conflicting labels, changed references and mismatched context cannot establish authenticity. Duplicate is a separate observation and can coexist with a Genuine result. Existing completed 3.5 assessments remain compatible; recheck a file to add dataset evidence.

### Signed document wallet and encrypted IPFS vault

Document wallet connects an EIP-6963 or injected Ethereum wallet using expiring, one-use EIP-191 signatures. Sepolia connections request chain ID 11155111. Each Veris login independently proves wallet ownership. The same address may be linked to multiple logins, but files, signatures and permissions remain scoped to the authenticated user. An existing login cannot silently replace its linked wallet. Startup migrates the former global wallet-address uniqueness rule while preserving existing links and document records. New connections open the wallet account chooser; setup help directs new users to create their wallet privately in MetaMask. Every save requires separate consent binding the original SHA-256, document ID and record network. Users retain their wallet private keys; the backend relay sponsors test-network gas.

The backend encrypts originals using AES-256-GCM, uploads only ciphertext to Pinata IPFS, and records the opaque document ID, owner address, original fingerprint, encrypted CID and consent commitment in VerisVault.sol. Documents are not literally stored inside MetaMask or on Ethereum. Decryption keys are backend-managed, derived from VAULT_ENCRYPTION_KEY. Keep that master key backed up: losing it prevents IPFS retrieval. This is not end-to-end or wallet-key encryption. Public on-chain owner addresses and commitments are visible on Sepolia; personal document contents remain encrypted off-chain.

Set PINATA_JWT, VAULT_ENCRYPTION_KEY (32 random bytes as URL-safe base64), VAULT_NETWORK=sepolia, VAULT_SEPOLIA_RPC_URL and a funded test-only VAULT_PRIVATE_KEY in backend environment variables. Compile with node contracts/compile-vault.mjs, deploy using python backend/deploy_vault.py --journal PRIVATE_PERSISTENT_PATH, then set VAULT_CONTRACT_ADDRESS to the actual returned address. Retain the deployment journal for crash recovery. Never put private keys or Pinata credentials in frontend variables. AUTO_ANCHOR=true processes queued wallet saves as well as the existing independent fraud ledger.

The wallet vault and fraud ledger use separate network configuration and contracts; deploying the Sepolia vault does not migrate or reset the existing private fraud audit. Signed save transactions are persisted before broadcast. A successful receipt, canonical block, emitted event and contract fields must all match before the UI reports a confirmed record. Authenticated IPFS retrieval validates ciphertext integrity, decrypts it and checks the original fingerprint. Save failures and unavailable proofs remain explicit; storage success never makes a document Genuine.

Reference review: the supplied employee report/repository and hospital ZIP informed the wallet/IPFS/Sepolia workflow. Their public upload patterns and unrelated insurance labels were not copied into production. The Telugu voice notes describe faculty/student reference datasets and the wallet/faucet flow; no official faculty or student registry was supplied, so no fabricated registry is presented as live institutional evidence.

Validation of this integration includes replay/wrong-signer/account-isolation tests, expired consent, changed originals, authenticated encryption tampering, dataset conflicts and compatibility with existing Genuine assessments. A separate isolated integration performed actual Pinata IPFS upload and retrieval plus real disposable Ganache contract deployment, registration and receipt checks. Sepolia readiness requires its own actual deployed contract and funded writer; local-chain test success alone does not establish a Sepolia deployment.

Hosted vault deployment (12 October 2026): Ethereum Sepolia, chain 11155111, contract [0xCdC2f287653bAcA5E5801cC551d93f738C5cFd5B](https://sepolia.etherscan.io/address/0xCdC2f287653bAcA5E5801cC551d93f738C5cFd5B). Deployment receipt: [0xcaab19a7d402ee43d3f99e547e0c0eb259124870abbd92fd1856a29f63a13610](https://sepolia.etherscan.io/tx/0xcaab19a7d402ee43d3f99e547e0c0eb259124870abbd92fd1856a29f63a13610). A controlled integration, isolated from production user records, stored an encrypted file and checked its real contract receipt at block 11899264; [the test transaction](https://sepolia.etherscan.io/tx/0xf685e24d5cd8247239de02e0a0a870932493dc11544edc0e0da3390a48d3e89c) matched its owner, original hash, CID and consent commitment. Retrieval from Pinata IPFS decrypted to the exact original bytes. The separately funded relay is configured on Railway; users approve their own wallet connection and each document save. Backend requirements resolve successfully and 80 backend regression checks passed across full and targeted runs, including staging tampering and substituted-contract proof rejection.


### Document classification and category datasets

The six evidence categories now have 23 specific document types, plus a cross-category institutional report type. Each completed verification run saves a separate document-type assessment in its metadata and PDF report. Classification uses versioned, explainable heading/field rules and exact curated type annotations. It does not grant authenticity or derive its answer from the uploaded filename or selected category. Ambiguous and unsupported content is not forced into a class; category mismatches are visible independently of authenticity.

Dataset references includes category/type coverage, downloadable public originals and CSV/JSON classification labels. The starter type corpus has eight annotations covering one type in each evidence category plus two NIRF institutional reports. Other types show their actual empty coverage. The authenticity reference pack retains the twelve controlled fake/neutral fixtures. No custom model has been trained and no independent accuracy is claimed.

Invited reviewers can add sourced type examples with a separately established authenticity label, issuer, period, provenance and evidence. These research annotations do not automatically become trusted authenticity references. Manipulated samples require an intact parent and a specific alteration; derivatives inherit the parent source family and research split. Exports reserve source families in deterministic train/validation/test buckets. Private reference files and annotations stay reviewer-restricted.

See backend/datasets/CLASSIFICATION_DATASET_CARD.md for taxonomy, source/label scope, collection requirements and evaluation boundaries. Run python backend/evaluate_classification.py --output evaluation.json to replay the development corpus without exact-reference lookups. This diagnostic reports type counts and a confusion matrix; it explicitly does not represent an independent held-out benchmark.
