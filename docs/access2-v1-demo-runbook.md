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

For controlled local demos, start the current-workspace frontend and wait for HTTP readiness with:

```powershell
cd C:\dev\access2
.\scripts\start-access2-demo-frontend.ps1
```

The helper starts the frontend on `http://localhost:3001`, waits for `http://localhost:3001/login`, and prints the process id to stop after the demo. Do not start Selenium until the helper reports that `/login` is reachable.

Known local tool notes:

- Pytest may emit local `.pytest_cache` permission warnings.
- Next lint/build may show the existing plugin configuration warning.

## 5a. Local Demo Readiness Checklist

Run these checks before starting the manual frontend demo script in [access2-v1-frontend-demo-script.md](C:/dev/access2/docs/access2-v1-frontend-demo-script.md). They separate environment readiness, auth readiness, demo data readiness, and audit bundle readiness.

### Environment readiness

1. Confirm Docker Desktop is running.

```powershell
cd C:\dev\access2
docker compose ps
```

Expected result:

- Docker responds without `failed to connect to the docker API`.
- If you see a Docker API or named-pipe error, start Docker Desktop first, then rerun the command.

2. Start the backend stack if it is not already running.

```powershell
cd C:\dev\access2
docker compose up --build
```

Expected result:

- `access2-postgres`, `access2-redis`, and `access2-backend` start.
- `postgres` and `redis` become healthy before the backend is ready.

3. In a second PowerShell window, confirm the containers are up.

```powershell
cd C:\dev\access2
docker compose ps
```

Expected result:

- The backend, postgres, and redis services are listed.
- If the backend exits or restarts repeatedly, inspect the Docker Compose logs before running the frontend demo.

4. Confirm backend health.

```powershell
$BackendBase = "http://localhost:8000/api/v1"
Invoke-WebRequest -UseBasicParsing -Uri "$BackendBase/health/live"
Invoke-WebRequest -UseBasicParsing -Uri "$BackendBase/health/ready"
```

Expected result:

- `/health/live` returns HTTP 200 when the backend process is alive.
- `/health/ready` returns HTTP 200 only when database and Redis checks pass.
- If `/health/ready` returns 503 or is unreachable, do not run the manual frontend demo yet.

5. Start the current-workspace frontend for the demo.

```powershell
cd C:\dev\access2
.\scripts\start-access2-demo-frontend.ps1
```

Expected result:

- The helper reports `Frontend is reachable at http://localhost:3001/login (HTTP 200)`.
- Use `http://localhost:3001` for the manual frontend demo.
- If port `3001` is already in use, follow the helper output and stop the stale process or choose a clean port.

### Auth readiness

Use the documented local demo account only if your local seed data includes it:

```text
admin@example.com / Admin123!
```

Check backend auth directly before trying the browser login:

```powershell
$BackendBase = "http://localhost:8000/api/v1"
$Login = Invoke-RestMethod `
  -Method Post `
  -Uri "$BackendBase/auth/login" `
  -ContentType "application/json" `
  -Body (@{
    email = "admin@example.com"
    password = "Admin123!"
  } | ConvertTo-Json)

$Headers = @{
  Authorization = "Bearer $($Login.access_token)"
}

Invoke-RestMethod -Method Get -Uri "$BackendBase/auth/me" -Headers $Headers
```

Expected result:

- Login returns an access token.
- `/auth/me` returns the authenticated user.
- If this fails with `401`, the account is not present or the password is different in this local database.
- If this fails with connection errors, backend/auth is not reachable.

Observed failure and meaning:

```text
Unable to sign in right now. Please try again.
```

This means the frontend login page loaded, but the frontend could not complete backend auth. Check, in order:

- Docker Desktop is running.
- `docker compose ps` shows backend, postgres, and redis running.
- `$BackendBase/health/ready` returns HTTP 200.
- `NEXT_PUBLIC_API_BASE_URL` points to the same backend, usually `http://localhost:8000/api/v1`.
- The seeded admin account exists in the current local database.

### Demo data readiness

The frontend audit demo needs persisted patient and review-packet data. A plain login is not enough.

1. Confirm patient/worklist data through the frontend smoke path after backend and auth are ready.

```powershell
cd C:\dev\access2
py -3 -m pytest tests/e2e/test_access2_smoke.py --e2e-base-url http://localhost:3001 -q -rs
```

Expected result:

- The login and read-only smoke checks pass.
- Some data-creating checks may be skipped unless `--e2e-submit-bootstrap` is supplied.

2. If you need to create a disposable validation patient, use the existing guarded bootstrap path against a disposable local database.

```powershell
cd C:\dev\access2
py -3 -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_submit_workflow_bootstrap --e2e-submit-bootstrap --e2e-base-url http://localhost:3001 -q
```

Expected result:

- The bootstrap path creates a validation patient for queue/detail smoke coverage.
- This creates data. Use it only against a disposable local database.

3. Confirm at least one persisted snapshot exists before expecting audit-readiness rows.

```powershell
$BackendBase = "http://localhost:8000/api/v1"
Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBase/reports/access-review-packet/audit-readiness" `
  -Headers $Headers
```

Expected result:

- `total_count` is greater than `0`, or `items` contains rows.
- If no rows exist, create or seed review-packet snapshots before running the full audit-readiness demo.

### Audit bundle and verification readiness

Approved bundle download and verification require more than a snapshot.

- JSON, Markdown, and PDF bundle downloads appear only where the patient backlog contains an approved export-ready snapshot.
- Non-approved snapshots should show `Unavailable until approved.`
- Rejected snapshots should show `Unavailable for rejected snapshots.`
- Verification requires a real `audit_manifest` copied from an exported JSON audit bundle.
- A copied manifest must match the snapshot ID being verified.

Use audit-readiness rows to find candidates:

```powershell
$BackendBase = "http://localhost:8000/api/v1"
Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBase/reports/access-review-packet/audit-readiness?status=approved_not_exported" `
  -Headers $Headers

Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBase/reports/access-review-packet/audit-readiness?status=audit_ready" `
  -Headers $Headers
```

Expected result:

- Rows with `audit_bundle.available = true` are candidates for approved bundle download.
- Rows with `audit_bundle.exported = true` have already recorded at least one successful audit bundle export.
- If no approved/export-ready rows exist, the manual frontend demo can still show unavailable states, but cannot complete JSON/Markdown/PDF download or manifest verification.

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
