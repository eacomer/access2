# ACCESS2 V1 Final Validation Checklist

## 1. Purpose

Use this checklist to validate the ACCESS2 V1 demo path without expanding scope:

login -> patient/worklist -> intervention/outcome evidence -> review packet -> approval -> audit bundle export -> verification

The goal is to confirm ACCESS2 can show audit-ready evidence for CMS ACCESS-style outcome review while preserving immutable review packet and read-only audit invariants.

## 2. Preconditions

- Backend and frontend dependencies are installed.
- Chrome and Selenium dependencies are available for E2E checks.
- A seeded admin account is available: `admin@example.com` / `Admin123!`.
- Run validation against a disposable local database when using data-creating Selenium bootstrap tests.
- `frontend/.env.local` may exist locally but must remain uncommitted.
- `frontend/tsconfig.tsbuildinfo` is generated and must remain uncommitted.

## 3. Git Hygiene Check

From repo root:

```powershell
cd C:\dev\access2
git status --short
git diff --stat
```

Expected local-only files may include:

```text
?? frontend/.env.local
?? frontend/tsconfig.tsbuildinfo
```

Stop and investigate before continuing if backend files, frontend app files, tests, or generated artifacts are unexpectedly modified.

## 4. Backend Validation

Run backend validation when backend code, migrations, review packet logic, audit bundle logic, or seed behavior changed:

```powershell
cd C:\dev\access2\backend
py -3 -m alembic -c alembic.ini upgrade head
py -3 -m pytest tests/test_access_review_packet.py -q
```

For frontend-only or docs-only validation passes, record why backend tests were not run.

## 5. Frontend Validation

From the frontend directory:

```powershell
cd C:\dev\access2\frontend
& "C:\Program Files\nodejs\npm.cmd" test
& "C:\Program Files\nodejs\npm.cmd" run lint
& "C:\Program Files\nodejs\npm.cmd" run build
.\node_modules\.bin\tsc.cmd --noEmit
```

Expected current API-helper result: 8 passing tests.

## 6. Seeded Selenium Validation

The Selenium README documents the seeded path in `tests/e2e/README.md`.

Seed one local patient through the existing admin workflow bootstrap UI:

```powershell
cd C:\dev\access2
py -3 -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_submit_workflow_bootstrap --e2e-submit-bootstrap -q
```

Then run the smoke suite:

```powershell
py -3 -m pytest tests/e2e/test_access2_smoke.py -q
```

If an already-running frontend on `localhost:3000` is stale, read-only audit panel checks can fail even when committed code is correct. Restart the `localhost:3000` frontend, or start a fresh current-workspace frontend on another port and pass that URL:

```powershell
py -3 -m pytest tests/e2e/test_access2_smoke.py --e2e-base-url http://localhost:3001 -q
```

Latest known seeded result against a fresh `localhost:3001` frontend: `5 passed, 9 skipped`.

## 7. Manual Audit-Readiness Page Checks

Open the frontend and log in as admin.

Check `/audit-readiness`:

- Page renders without a fatal error.
- Status filters are visible: Incomplete, Review ready, Approved not exported, Audit ready, Rejected.
- Reviewer workload summary renders when the reviewer summary endpoint is available.
- Audit-readiness table renders persisted latest-snapshot rows or a clean empty state.
- Page remains read-only.

## 8. Manual Patient Detail Audit Checks

Open `/patients?active_only=0` and choose a seeded patient card.

On patient detail, verify:

- Existing patient workflow header renders.
- Patient evidence/timeline content renders.
- `patient-audit-status-panel` renders.
- `patient-review-packet-backlog-panel` renders.
- Audit-status panel shows snapshot, review state, next step, and completion.
- Review-packet backlog section shows snapshot presence, total snapshot count, next step, completion, and latest snapshot metadata when available.
- Empty snapshot states are clear and read-only.

## 9. Read-Only Guardrail Checks

The following controls must not appear in read-only audit sections unless explicitly requested for a controlled mutation slice:

- Approve
- Reject
- Assign
- Export Bundle
- Verify
- Create Snapshot

Read-only endpoints must not create events, rebuild snapshots, mutate `packet_json`, or mutate `packet_markdown`.

## 10. Optional Backend Audit Bundle Spot Checks

When validating audit bundle flows, spot-check that:

- Snapshot data remains immutable after creation.
- Audit bundle export logs events only after successful export.
- Verification compares supplied manifests against persisted snapshot data.
- Tenant-scoped requests do not expose another tenant's patients, snapshots, packets, or bundles.

Use focused backend tests for any defect found here before changing product behavior.

## 11. V1 Pass Criteria

V1 validation passes when:

- Login succeeds.
- `/audit-readiness` renders and remains read-only.
- `/patients?active_only=0` renders seeded patient cards.
- Patient detail renders existing workflow and evidence content.
- Patient audit-status panel renders.
- Patient review-packet backlog panel renders.
- Read-only audit sections expose no mutation controls.
- Frontend validation commands pass.
- Selenium seeded smoke runs against current frontend code without the patient-card audit path skipping.
- No unexpected product-code, backend, test, or generated files are modified.

## 12. V1 Fail Criteria

Stop and record a defect if any of these occur:

- Required pages fail to render.
- Seeded patient cards are unavailable after the documented bootstrap path.
- Patient audit-status or backlog panels do not render on current frontend code.
- Read-only audit sections expose mutation controls.
- Read-only endpoints mutate data or create events.
- Snapshot or packet reads rebuild persisted audit artifacts.
- Tenant scoping appears broken.
- Validation requires backend, frontend, or test changes outside the current approved slice.
- Generated or local-only files are staged.

## 13. Follow-Up Recording Template

```text
Date:
Validator:
Branch/commit:
Frontend URL:
Backend URL:
Database/reset state:

Commands run:
- 

Results:
- Backend:
- Frontend:
- Selenium:
- Manual audit-readiness:
- Manual patient detail:

Defects found:
- 

Deferred follow-up:
- 

Files changed during validation:
- 
```
