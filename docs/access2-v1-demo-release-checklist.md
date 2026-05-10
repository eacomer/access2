# ACCESS2 V1 Demo Release Checklist

## Purpose

Use this checklist to decide whether the local ACCESS2 V1 demo is ready to show.

The demo release path is:

```text
login -> patient/worklist -> intervention/outcome evidence -> review packet -> approval -> audit bundle export -> verification
```

This checklist is for readiness validation only. It does not add product scope or replace the detailed runbook in [access2-v1-demo-runbook.md](C:/dev/access2/docs/access2-v1-demo-runbook.md) or the operator walkthrough in [access2-v1-frontend-demo-script.md](C:/dev/access2/docs/access2-v1-frontend-demo-script.md).

## Required Local Prerequisites

- Docker Desktop is running.
- Docker Compose stack is running.
- Backend health endpoints pass:
  - `/api/v1/health/live`
  - `/api/v1/health/ready`
- Frontend is running on the documented demo port: `http://localhost:3001`.
- Backend auth is reachable.
- Documented local demo credentials are available:

```text
admin@example.com / Admin123!
```

- Seeded/demo patient data exists.
- At least one patient has a persisted review-packet snapshot.
- At least one snapshot is approved and export-ready before demonstrating JSON, Markdown, PDF downloads, or manifest verification.
- A real `audit_manifest` from an exported JSON audit bundle is available for verification.

## Validated Frontend Surfaces

- `/login`
- `Patients`
- `Reviewer Queue` at `/audit-readiness`
- `Release Summary` at `/demo/release-summary`
- Patient detail page
- Patient `ACCESS audit status` panel
- Patient `Review packet backlog`
- Approved-only audit bundle downloads:
  - JSON
  - Markdown
  - PDF
- `/audit-bundle-verify`

## Validated Backend Capabilities Exercised

- Health checks.
- Auth login and current-user lookup.
- Patient/demo data availability.
- Immutable review-packet snapshot creation.
- Approval with documented override when local demo evidence is incomplete.
- Approved audit bundle export.
- Audit manifest verification against persisted snapshot data.

## Pre-Demo Validation Commands

Check git hygiene:

```powershell
cd C:\dev\access2
git status --short
git diff --stat
```

Start or verify the local stack:

```powershell
cd C:\dev\access2
docker compose ps
docker compose up --build
```

In a second PowerShell window, verify backend health:

```powershell
$BackendBase = "http://localhost:8000/api/v1"
Invoke-WebRequest -UseBasicParsing -Uri "$BackendBase/health/live"
Invoke-WebRequest -UseBasicParsing -Uri "$BackendBase/health/ready"
```

Start the current-workspace frontend:

```powershell
cd C:\dev\access2
.\scripts\start-access2-demo-frontend.ps1
```

Verify backend auth:

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

Run the existing frontend smoke check:

```powershell
cd C:\dev\access2
py -3 -m pytest tests/e2e/test_access2_smoke.py --e2e-base-url http://localhost:3001 -q -rs
```

If a disposable local database needs a validation patient, run the existing guarded bootstrap path:

```powershell
cd C:\dev\access2
py -3 -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_submit_workflow_bootstrap --e2e-submit-bootstrap --e2e-base-url http://localhost:3001 -q
```

Confirm audit-readiness rows:

```powershell
$BackendBase = "http://localhost:8000/api/v1"
Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBase/reports/access-review-packet/audit-readiness" `
  -Headers $Headers
```

Find approved/export-ready candidates:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBase/reports/access-review-packet/audit-readiness?status=approved_not_exported" `
  -Headers $Headers

Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBase/reports/access-review-packet/audit-readiness?status=audit_ready" `
  -Headers $Headers
```

## Expected Validation Results

- Backend live and ready checks return HTTP 200.
- Browser login succeeds with the documented demo account.
- `Reviewer Queue` shows read-only V1 copy, lifecycle counts, and at least one latest-snapshot row.
- `Release Summary` shows the read-only Evidence Proof Checklist for all four seeded synthetic demo patients.
- `Release Summary` shows the evidence chain from signal through manifest verification, plus readiness reasons and next step.
- A patient detail page opens from an audit-readiness row.
- Patient audit-status and review-packet backlog panels render.
- Approved bundle download links work for JSON, Markdown, and PDF where an approved export-ready snapshot exists.
- `/audit-bundle-verify` reports `Verified` when given the matching snapshot ID and real `audit_manifest`.
- Mismatch, invalid JSON, missing-field request error, auth error, and backend error states are understandable and do not expose stack traces.

Latest validated local result:

```text
Selenium smoke: 5 passed, 9 skipped
Bootstrap seed test: 1 passed
```

## Known Non-Blocking Warnings

- Existing Next.js ESLint plugin/configuration warning may appear during frontend validation.
- Windows LF/CRLF Git warnings may appear when docs are touched.
- Local pytest cache permission warnings may appear under `.pytest_cache` or `backend/.tmp/pytest_cache`.

## Known Blockers

- Docker Desktop is unavailable or Docker API/named pipe connection fails.
- Backend health is unreachable or `/health/ready` does not return HTTP 200.
- Login shows:

```text
Unable to sign in right now. Please try again.
```

- No seeded patients exist.
- No persisted review-packet snapshots exist.
- No approved export-ready snapshot exists for bundle downloads.
- No real JSON audit bundle `audit_manifest` exists for verification.
- `localhost:3000` is stale and does not reflect the current workspace.

## Commit Hygiene

Commit only intentional source and docs changes.

Do not commit:

```text
frontend/.env.local
frontend/tsconfig.tsbuildinfo
backend/.tmp/pytest_cache
```

Before commit, rerun:

```powershell
cd C:\dev\access2
git status --short
git diff --stat
```

## Final Demo Success Criteria

The V1 demo is ready to show when an operator can:

1. Sign in.
2. Open `Patients`.
3. Open `Reviewer Queue`.
4. Open `Release Summary`.
5. Explain the read-only Evidence Proof Checklist and expected production E2E baseline.
6. Explain the read-only Reviewer Work Queue and a patient audit-readiness row.
7. Navigate from that row to patient detail.
8. Explain patient workflow evidence, audit status, and review-packet backlog.
9. Download JSON, Markdown, and PDF audit bundles for an approved export-ready snapshot.
10. Copy `audit_manifest` from the JSON bundle.
11. Open `Verify Bundle`.
12. Verify the manifest against persisted snapshot data.
13. Explain mismatch, invalid JSON, missing-field, auth, and backend error states.

## Scope Reminder

Keep V1 focused on the validated audit path. Do not add AI, analytics, billing, EHR/FHIR, broad admin features, UI redesign, or new workflow mutation controls to make the demo look broader than it is.
