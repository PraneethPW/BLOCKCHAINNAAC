# Veris — Accreditation evidence review

Independent working prototype. Not an official NAAC service. Does not issue accreditation grades.

## Included

- React, TypeScript, Tailwind CSS, Framer Motion and a procedural Three.js evidence vault. Scroll and pointer movement control the scene; reduced-motion preferences are supported.
- Institution and reviewer workspaces: uploads, search, status filters, extracted text, source comparisons, review history, appeals, original-file downloads, PDF reports, source registration and audit trail.
- FastAPI, SQLAlchemy and Neon PostgreSQL. Salted scrypt passwords, expiring in-memory bearer tokens, ownership-scoped document access and separately provisioned reviewer roles.
- SHA-256 duplicate checks, exact issuer-file matches, and placement-count comparison with reviewer-registered source evidence for the same institution/category/period. A discrepancy starts an investigation, never a fraud finding.
- PDF text extraction and Tesseract OCR for image uploads. Scanned PDFs without a text layer currently require conversion to images for OCR. Digital-signature certificate trust and revocation validation are explicitly reported as unavailable.
- OpenRouter openrouter/free: explicit per-document consent, limited extracted text, provider data collection denied, and no paid-model fallback. AI is advisory and cannot change verification status.
- Solidity append-only ledger plus a private Ethereum development network and Sepolia anchoring adapter. Only confirmed findings and later appeals are anchored. Opaque IDs and hashes go on-chain; files and review narratives stay off-chain.

## Local development

Use Node 22+ and Python 3.12. In frontend, run `corepack enable`, `pnpm install`, then `pnpm dev`.

In backend, create/activate a virtual environment, run `pip install -r requirements.txt`, configure environment variables from .env.example, then run `uvicorn main:app --host 127.0.0.1 --port 8000`.

The API reads the process environment. To use a private .env file locally, start uvicorn with `--env-file .env`. Development falls back to SQLite; production requires PostgreSQL and a strong JWT_SECRET. Install Tesseract locally for image OCR; the Docker image includes it. The frontend defaults to the deployed Railway API. For a local backend, set VITE_API_URL=http://127.0.0.1:8000 in frontend/.env.local.

Choose Explore platform for a clearly labeled fictional demo. Real institution accounts can be created through Sign in → Create account. The browser demo saves only file metadata and fingerprints; original demo files are not retained or transmitted. Reset it in workspace settings.

## Reviewer access

Run `python provision_reviewer.py` in a secure backend shell with DATABASE_URL set. The script prompts for reviewer details and a password without echoing it. It creates a new reviewer and refuses to change an existing account. Reviewer roles cannot be selected at public registration.

## Verification walkthrough

1. Upload a report containing `100 students placed`, category Student placements, period `2025-26`.
2. Reviewer registers authorized issuer evidence in workspace settings with the same exact institution/category/period and confirmed placement count `40`.
3. Run checks again on the submission. The discrepancy is flagged; no blockchain entry is created.
4. Reviewer investigates and records a decision with a supporting evidence reference. Only a confirmed fraud finding creates an anchoring outbox entry.
5. The configured blockchain worker anchors it. An upheld appeal appends a linked record and preserves the earlier finding.

Issuer evidence is registered manually by authorized reviewers. No live NAAC, government or employer API connection is claimed. Matching files or counts do not independently verify every claim. Ambiguous counts remain investigative leads.

## Vercel

Import PraneethPW/BLOCKCHAINNAAC. Set Root Directory to frontend, framework Vite, build command `pnpm build`, output directory dist. Set VITE_API_URL to the Railway HTTPS API origin. Add the exact resulting Vercel origin to Railway FRONTEND_ORIGINS. Database URLs, OpenRouter keys and wallet keys must never be VITE variables.

## Railway

The backend service builds from /backend using Dockerfile and healthcheck /health. It listens on Railway PORT. Mount a persistent volume at /data and set UPLOAD_DIR=/data/uploads.

Required variables: DATABASE_URL, JWT_SECRET (random 32+ characters), APP_ENV=production, FRONTEND_ORIGINS (comma-separated exact origins), UPLOAD_DIR. AI variables: OPENROUTER_API_KEY and OPENROUTER_MODEL=openrouter/free. All credentials belong in Railway environment settings.

Tables use the veris_ prefix. Startup creates missing tables without changing unrelated data. Future schema changes require migrations. requirements.lock.txt records tested Windows package versions; the Linux Docker build uses requirements.txt because the Windows lock includes pywin32.

## Blockchain networks

In contracts, run `pnpm install`, `pnpm compile`, then `node test.mjs`. VerisLedger.json contains the compiled ABI and bytecode; backend/ledger_abi.json is used by the worker.

In a secure backend environment, configure SEPOLIA_RPC_URL and LEDGER_PRIVATE_KEY for a wallet with Sepolia test ETH. Run `python deploy_contract.py` with the compiled artifact available, or specify LEDGER_ARTIFACT. Set the returned LEDGER_CONTRACT_ADDRESS and LEDGER_START_BLOCK. Only chain ID 11155111 is accepted.

Run `python anchor_worker.py` as a single scheduled/dedicated worker. Postgres advisory locking prevents concurrent passes. The signed public transaction is persisted before broadcast so interrupted sends can retry. A successful receipt is required for anchored status. Duplicate record IDs cannot overwrite records; appeals must reference the prior confirmed finding. The contract restricts writers and has no update/delete path.

The hosted prototype uses a private Ganache network (chain ID 1337) on Railway, without a public RPC. Its /data volume retains chain history. Set LEDGER_NETWORK=private-devnet, LEDGER_RPC_URL to the private RPC, a random LEDGER_PRIVATE_KEY, and AUTO_ANCHOR=true. The worker creates test currency and deploys the compiled contract once, storing its public address in Neon. Missing persisted contract code stops writes instead of silently resetting history. This centrally operated development network demonstrates real Ethereum receipts; it does not provide independent consortium trust. Sepolia remains available with LEDGER_NETWORK=sepolia. Never switch an existing ledger database between networks without an explicit migration. Production needs finality monitoring, key custody, independent validators, backup and retention policies.

## Validation

- Frontend: `pnpm build` in frontend.
- API: `python -m pytest tests -q` in backend.
- Contract: `pnpm compile` and `node test.mjs` in contracts.

API tests cover ownership isolation, reviewer permissions, evidence requirements, automated-check boundaries, placement-count mismatches, append-only appeals, report PDFs, invalid files, AI consent and paid-model rejection. Contract checks cover writer permissions, duplicate prevention, valid outcomes, appeal linkage and preserved history. A Neon integration smoke test uses synthetic data in a transaction that is rolled back.

## Remaining production work

Institution identity is self-entered and needs authorized onboarding. Login throttling is per-process. Files use a private persistent volume; operational backup, encryption controls, malware scanning and retention require deployment policy. Real issuer APIs, cryptographic signer-chain validation, robust content similarity, consortium governance and immutable off-chain evidence storage remain future integrations. AI may be unavailable under rate limits or privacy constraints. This prototype is not certified production infrastructure.
