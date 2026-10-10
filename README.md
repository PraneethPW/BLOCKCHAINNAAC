# Veris — Connected accreditation evidence

Independent working prototype. No NAAC affiliation; no accreditation grades.

## Experience

React + TypeScript + Tailwind, Framer Motion, Three.js and GSAP ScrollTrigger. A continuous procedural evidence core responds to scroll and pointer movement across the landing page, authentication and workspace. Reduced motion, keyboard navigation, modal focus containment, responsive layouts and a WebGL fallback are included. There are no runtime sample users, seeded dashboards or fabricated verification responses.

## Authentication and access

Institution registration, login, logout and password changes use scrypt password hashes and eight-hour HttpOnly sessions. Production cookies are Secure and SameSite=Lax. JWT session IDs are stored in PostgreSQL and checked on requests; logout revokes the current session and password changes revoke all sessions. State-changing cookie requests require an application header and allowed Origin. Ownership checks protect files, reports, decisions and ledger visibility. Reviewer access requires a hashed, expiring, single-use invitation or authorized backend provisioning.

Use your own account. Issue a private reviewer invitation from an authorized backend shell with python provision_invitation.py --days 7. Do not publish invitation codes. No reviewer role selector is available to public users. Institution identity is self-entered until an authorized onboarding process is connected; email ownership verification and recovery email are not configured.

## Verification

Uploaded originals receive an exact SHA-256 fingerprint and a durable database job. A background worker records committed stages, timestamps, errors and provider results. PostgreSQL advisory locking serializes worker passes and interrupted jobs are retried after five minutes. Stored bytes are rehashed before processing; an integrity mismatch stops verification while retaining evidence.

The worker extracts bounded native PDF text, runs Tesseract OCR on images and up to twelve scanned PDF pages, inspects PDF metadata, signature fields and active actions, detects duplicate fingerprints and repeated normalized text in the same institutional context. Reviewer-registered issuer records support exact-file comparisons and placement counts for matching institution/category/period. Originals are authenticated downloads, never executed inside the app.

Extracted DOI identifiers (up to eight per pass) are checked directly against Crossref, DataCite and Europe PMC. Each provider result records the requested identifier, endpoint, time, returned metadata and found/not-found/unavailable state. Only fixed registry hosts are contacted; uploaded URLs are never fetched. A registry match corroborates metadata, not affiliation or document authenticity. Missing records and provider outages never establish fraud. Documents without public identifiers require authorized issuer evidence.

SSE events announce actual workspace changes, with authenticated reconnects and a periodic refresh fallback. Search and status filters query PostgreSQL and the library paginates all matching records. Evidence views expose findings, public responses, extraction metadata, processing history, decisions and receipt status. PDF reports include check results, source provenance, decisions, transaction hashes and optional advisory notes.

OpenRouter assistance requires explicit document consent, sends at most 12,000 extracted characters, denies provider data collection and uses only a :free model or openrouter/free. AI returns investigation advice and never changes review status. Capacity or privacy-policy failures appear as errors; no paid or fabricated fallback is used.

Only supported authorized decisions establish verified or confirmed-fraud status. Confirmed findings and upheld appeals create append-only blockchain records containing opaque IDs and hashes. Sensitive files and narratives remain off-chain. Appeals preserve the earlier finding. Anchored status requires an actual successful transaction receipt.

## Local development

Use Node 22+ and Python 3.12. In frontend: pnpm install, then pnpm dev. In backend: create a virtual environment, pip install -r requirements.txt, configure .env.example values in the process environment, then uvicorn main:app --host 127.0.0.1 --port 8000. Use --env-file .env if needed. Install Tesseract locally for OCR; the Docker image includes it. AUTO_VERIFY=true enables the processing loop. Development can use SQLite; production requires PostgreSQL and a strong JWT_SECRET.

The frontend calls same-origin /api. Vite proxies it to localhost:8000; frontend/vercel.json proxies it to the Railway API. This keeps sessions on the frontend origin. No database, AI or wallet credential belongs in frontend variables.

## Hosting

Vercel: import PraneethPW/BLOCKCHAINNAAC, root frontend, framework Vite, build pnpm build, output dist. Update the proxy destination if the backend domain changes. Add the exact frontend HTTPS origin to Railway FRONTEND_ORIGINS.

Railway API: root /backend, Dockerfile, healthcheck /health, PORT supplied by Railway. Mount /data and set UPLOAD_DIR=/data/uploads. Set DATABASE_URL, JWT_SECRET (32+ random characters), APP_ENV=production, FRONTEND_ORIGINS, AUTO_VERIFY=true, OPENROUTER_API_KEY and OPENROUTER_MODEL. The hosted free model is dots-studio/dots-3-note-preview:free; availability can change.

Tables use the veris_ prefix. Startup creates missing tables without changing unrelated data. Archive rows hide prior QA records and deny archived account access without deleting evidence or blockchain history. Future schema changes require migrations.

## Blockchain

The current hosted network is private Ganache, chain ID 1337, accessible only over Railway private networking. Its persistent /data volume retains history. LEDGER_NETWORK=private-devnet, LEDGER_RPC_URL, LEDGER_PRIVATE_KEY and AUTO_ANCHOR=true configure anchoring. The deployed contract address is retained in Neon; missing contract code stops writes rather than resetting history. Signed transactions are persisted before broadcast and advisory locking prevents concurrent worker passes.

This network produces real Ethereum receipts but is centrally operated development infrastructure. Independent validator governance, key custody, finality policy and backups are needed for a consortium deployment. Sepolia remains supported via LEDGER_NETWORK=sepolia, SEPOLIA_RPC_URL, LEDGER_CONTRACT_ADDRESS and a funded test wallet. Never switch an existing ledger database between networks without a migration.

Contract commands in contracts: pnpm install, pnpm compile, node test.mjs. Backend anchoring: python anchor_worker.py. The contract restricts writers, prevents duplicate IDs and validates appeal linkage. It has no record update or delete path.

## Validation

Frontend: pnpm build. Backend: python -m pytest tests/test_workflow.py -q. Tests use isolated temporary databases and provider test doubles only within tests; they are not runtime fallbacks. Tests cover isolation, review authorization, append-only appeals, issuer counts, file validation, AI consent/free-model rules, cookie CSRF, logout/password revocation, invitation reuse, durable jobs, tamper detection, archival and server-side pagination/search.

A live local integration pass queried a publication DOI: Crossref and Europe PMC returned records, DataCite returned not-found, and review status remained unverified. OpenRouter returned real advisory text without changing status. Browser QA covers 375px phone, 768px tablet, 1440px desktop and short landscape navigation, cookie restoration, source views, motion controls and logout.

## Boundaries and operational work

Public scholarly APIs cannot authenticate placement letters, financial statements, certificates or institutional ownership without issuer access. Signature fields are detected, but cryptographic signer-chain/revocation validation is not configured. Extraction and OCR have explicit resource bounds. Login throttling is per process. Session rows and jobs are durable; deployment-scale rate limiting, malware scanning, email verification/recovery, encryption and retention policies, backups, immutable off-chain storage and independent validator governance remain operational work. This is a working independent prototype, not certified production accreditation infrastructure.
