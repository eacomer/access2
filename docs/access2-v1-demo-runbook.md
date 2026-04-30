# ACCESS2 V1 Demo Runbook

## 1. Purpose

Use this runbook for a controlled local ACCESS2 V1 demo or pilot-review session.

The demo shows the validated read-only audit visibility baseline for the CMS ACCESS-aligned evidence path:

```text
signal -> escalation -> intervention -> outcome -> care update -> resolution -> evidence -> case summary -> immutable review packet -> approval -> audit bundle
```

This runbook is not a production operations guide and does not claim the full mutation workflow is complete.

## 2. What This Demo Proves

- ACCESS2 can show organization-level audit readiness from persisted workflow and review-packet data.
- ACCESS2 can link patient-level audit posture to review packets and audit-readiness views.
- ACCESS2 can show evidence posture for a seeded patient without adding mutation controls to read-only audit panels.
- The current read-only V1 audit visibility baseline has been validated locally with backend, frontend, and Selenium checks.

Latest validated baseline:

- Backend review packet and audit bundle behavior: `91 passed`.
- Alembic upgrade head: passed.
- Frontend API-helper tests: `8 passed`.
- Frontend lint, build, and typecheck: passed.
- Seeded Selenium validation against fresh `http://localhost:3001`: `5 passed, 9 skipped`.
- Manual read-only checks: passed.

## 3. What This Demo Does Not Yet Prove

- It does not prove that all mutation workflows are complete in the UI.
- It does not demonstrate approve, reject, assign, export, verify, or create-snapshot actions from read-only audit panels.
- It does not demonstrate real CMS submission, EHR integration, FHIR integration, billing, payment reconciliation, AI recommendations, or predictive analytics.
- It does not replace targeted backend validation for future mutation, export, or verification slices.

## 4. Preconditions

- Run against a disposable local database when using the Selenium bootstrap path.
- Backend and frontend dependencies are installed.
- Chrome and Selenium dependencies are available.
- The seeded admin account is available:

```text
admin@example.com / Admin123!
```

- Local-only files may exist but must remain uncommitted:

```text
frontend/.env.local
frontend/tsconfig.tsbuildinfo
```

Before starting, check git hygiene:

```powershell
cd C:\dev\access2
git status --short
git diff --stat
```

Stop before demo prep if unexpected backend files, frontend app files, tests, generated artifacts, or unrelated docs are modified.

## 5. Startup and Environment Notes

Start ACCESS2 the same way you normally run local development. A typical Docker path is:

```powershell
cd C:\dev\access2
docker compose up --build
```

If running services separately, start the backend first, then start the Next.js frontend with its API base URL pointed at the running backend.

Typical local URLs:

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000 or http://127.0.0.1:8001
```

Warning: `localhost:3000` can be stale if an older frontend server is still running. If audit panels do not appear even though the code is current, restart `localhost:3000` or start a fresh current-workspace frontend on another port such as `http://localhost:3001`.

The latest validated local read-only demo path used `http://localhost:3001`.

Known local tool notes:

- Pytest may emit local `.pytest_cache` permission warnings.
- Next lint/build may show the existing plugin configuration warning.

## 6. Seeded Patient Setup

Seed one local patient through the existing admin workflow bootstrap UI:

```powershell
cd C:\dev\access2
py -3 -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_submit_workflow_bootstrap --e2e-submit-bootstrap --e2e-base-url http://localhost:3001 -q
```

Then run the seeded Selenium smoke path against the same fresh frontend:

```powershell
cd C:\dev\access2
py -3 -m pytest tests/e2e/test_access2_smoke.py --e2e-base-url http://localhost:3001 -q
```

Expected latest seeded smoke result against a fresh `localhost:3001` frontend:

```text
5 passed, 9 skipped
```

The 9 skipped tests are expected for the read-only smoke command. They are data-creating bootstrap, patient-detail mutation, workflow alignment, and escalation mutation checks that require `--e2e-submit-bootstrap` and a disposable local database. If the first 5 tests fail with `net::ERR_CONNECTION_REFUSED`, the selected frontend URL is not running or reachable; start or restart the frontend before interpreting the smoke result.

## 7. Demo Flow

1. Open the frontend.
2. Log in as the seeded admin.
3. Visit:

```text
/audit-readiness
```

Viewer should see:

- Reviewer workload summary.
- Audit-readiness table.
- Read-only audit posture and clean empty states where applicable.
- No approve, reject, assign, export, verify, or create-snapshot controls in read-only audit sections.

4. Visit:

```text
/patients?active_only=0
```

Viewer should see seeded patient cards after the bootstrap path has run.

5. Open a seeded patient detail page.

Viewer should see:

- Existing patient workflow header.
- Patient evidence and timeline content.
- Patient audit-status panel.
- Patient review-packet backlog panel.
- Snapshot, review state, next step, completion, and latest snapshot metadata where available.
- No mutation controls in read-only audit panels.

## 8. Suggested Talk Track

ACCESS2 is proving evidence posture, not just displaying tasks. The point of this V1 read-only demo is to show how the system connects patient-level workflow evidence to review packets and audit readiness.

On `/audit-readiness`, call out the reviewer workload summary and the audit-readiness table. These views help reviewers understand where evidence stands without mutating the underlying audit record.

On patient detail, call out the audit-status and review-packet backlog panels. These connect the patient's current audit posture to persisted review packet history and make the next review step visible.

Mutation workflows and export/verification UI are intentionally deferred from this read-only V1 demo. Approve, reject, assign, export, verify, and create-snapshot actions should be demonstrated only in a future controlled mutation slice after that behavior is explicitly implemented and validated.

## 9. Read-Only Guardrails to Call Out

- Read-only audit panels should not expose approve, reject, assign, export, verify, or create-snapshot buttons.
- Read-only endpoints must not mutate data.
- Snapshot and packet reads must not rebuild persisted `packet_json` or `packet_markdown`.
- Audit bundle export events should be logged only after successful export.
- Audit bundle verification must compare supplied manifests against persisted snapshot data.
- Tenant scoping and patient consistency must remain preserved across linked records.

## 10. Known Limitations

- This is a controlled local demo and pilot-review runbook, not a production deployment guide.
- `localhost:3000` can be stale unless restarted.
- The current demo emphasizes read-only audit visibility and evidence posture.
- Full UI mutation workflows are not represented by this runbook.
- Export and verification UI remain outside this read-only demo path.
- Selenium may skip paths when seeded patient cards are unavailable.
- Local generated files must remain uncommitted.

## 11. Stop Conditions

Stop the demo or validation pass and record a defect if:

- `/audit-readiness` does not render.
- `/patients?active_only=0` does not show seeded patient cards after bootstrap.
- Patient detail does not render.
- The patient audit-status panel is missing.
- The patient review-packet backlog panel is missing.
- Read-only audit sections expose approve, reject, assign, export, verify, or create-snapshot controls.
- Read-only audit checks appear to mutate data.
- Snapshot or packet reads appear to rebuild persisted audit artifacts.
- Tenant scoping or patient consistency appears broken.
- Validation requires backend code, frontend app code, tests, or generated artifact changes outside the approved slice.
- `frontend/.env.local`, `frontend/tsconfig.tsbuildinfo`, or other generated artifacts are staged.

## 12. Follow-Up Notes Template

```text
Date:
Reviewer:
Branch/commit:
Frontend URL:
Backend URL:
Database/reset state:

Commands run:
- 

Screens visited:
- /audit-readiness
- /patients?active_only=0
- Patient detail:

Observed:
- Reviewer workload summary:
- Audit-readiness table:
- Patient audit-status panel:
- Patient review-packet backlog panel:
- Mutation controls absent from read-only audit panels:

Results:
- Selenium bootstrap:
- Selenium smoke:
- Manual audit-readiness:
- Manual patient detail:

Defects found:
- 

Deferred follow-up:
- 

Files changed during demo prep:
- 
```
