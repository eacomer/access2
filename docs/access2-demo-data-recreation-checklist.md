# ACCESS2 Demo Data Recreation Checklist

## Purpose

Use this checklist to recreate the minimum local data needed for the ACCESS2 V1 demo path after a local database reset or on a new developer machine.

Validated demo path:

```text
login -> patient/worklist -> intervention/outcome evidence -> review packet -> approval -> audit bundle export -> verification
```

This checklist uses existing documented runbook, Selenium bootstrap, and operator-flow steps. It does not introduce new seed scripts, endpoints, or product behavior.

## When To Use This

Use this checklist when:

- A local database was reset.
- A new developer is preparing a local demo environment.
- `Audit Readiness` has no latest-snapshot rows.
- Bundle download or verification cannot be demonstrated because no approved export-ready snapshot exists.

## Required Prerequisites

Start with the local readiness steps in [access2-v1-demo-runbook.md](C:/dev/access2/docs/access2-v1-demo-runbook.md).

Required state:

- Docker Desktop is running.
- Docker Compose stack is running.
- Backend health passes:
  - `/api/v1/health/live`
  - `/api/v1/health/ready`
- Frontend is running at `http://localhost:3001`.
- Backend auth is reachable.
- Documented local credentials work:

```text
admin@example.com / Admin123!
```

- Local/generated files remain uncommitted:
  - `frontend/.env.local`
  - `frontend/tsconfig.tsbuildinfo`
  - `backend/.tmp/pytest_cache`

## Minimum Demo Data State

The demo needs:

- At least one patient.
- At least one persisted review-packet snapshot.
- At least one snapshot approved normally, or approved with the documented local override path when evidence is incomplete.
- Audit bundle available/exported status for that snapshot.
- JSON, Markdown, and PDF bundle formats available where expected.
- A real JSON audit bundle `audit_manifest`.
- Successful audit bundle verification with that manifest.

## Data Recreation Steps

### 1. Start And Verify Local Services

Use the documented runbook commands:

```powershell
cd C:\dev\access2
docker compose ps
docker compose up --build
```

In a second PowerShell window:

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

Expected result:

- Backend health returns HTTP 200.
- The frontend helper reports `Frontend is reachable at http://localhost:3001/login (HTTP 200)`.

### 2. Confirm Auth Works

Use the documented local demo account only if this local seed data includes it:

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

### 3. Confirm Or Create A Patient

First, run the existing smoke path to confirm login and worklist behavior:

```powershell
cd C:\dev\access2
py -3 -m pytest tests/e2e/test_access2_smoke.py --e2e-base-url http://localhost:3001 -q -rs
```

If a disposable local database needs a validation patient, use the existing guarded bootstrap path:

```powershell
cd C:\dev\access2
py -3 -m pytest tests/e2e/test_access2_smoke.py::test_admin_can_submit_workflow_bootstrap --e2e-submit-bootstrap --e2e-base-url http://localhost:3001 -q
```

Expected result:

- A validation patient is available for queue/detail smoke coverage.
- This creates data. Use it only against a disposable local database.

### 4. Create Or Confirm A Persisted Snapshot

Check audit readiness first:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBase/reports/access-review-packet/audit-readiness" `
  -Headers $Headers
```

Expected result:

- If `total_count` is greater than `0`, capture a `patient_id` and `latest_snapshot_id`.
- If no rows exist, create a persisted snapshot using the existing operator flow in [access-review-packet-operator-flow.md](C:/dev/access2/docs/access-review-packet-operator-flow.md).

Operator-flow variables:

```powershell
$BACKEND_URL = "http://localhost:8000/api/v1"
$TOKEN = "<token>"
$PATIENT_ID = "<patient-id>"

$Headers = @{
  Authorization = "Bearer $TOKEN"
}
```

Create the immutable snapshot:

```powershell
$Snapshot = Invoke-RestMethod `
  -Method Post `
  -Uri "$BACKEND_URL/reports/access-review-packet/$PATIENT_ID/snapshots" `
  -Headers $Headers

$SNAPSHOT_ID = $Snapshot.id
$Snapshot
```

Expected result:

- Snapshot metadata is returned.
- `packet_json` and `packet_markdown` are persisted.
- Review status starts as `pending_review`.

V2 reviewer rejection mutation testing requires a snapshot that is still `pending_review`. Production Demo Patient 3 is intentionally seeded as already rejected, so it is useful for read-only rejected-posture validation but not for repeatable rejection mutation E2E. Do not activate production rejection mutation tests until reset/reseed instructions define how shared demo data is restored.

### Local V2 Reviewer Rejection Mutation Seed

Use this local-only seed/reset path only against a disposable local database when preparing future reviewer rejection mutation testing:

```powershell
cd C:\dev\access2\backend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:PYTHONPATH="C:\dev\access2\backend"
py -3 -m scripts.seed_local_v2_rejection_mutation
```

The script at `backend/scripts/seed_local_v2_rejection_mutation.py` creates or repairs one disposable synthetic patient with marker `access2-local-v2-mutation:reviewer-rejection`. Its latest review packet snapshot is `pending_review` with persisted `packet_json` and `packet_markdown`, so it is suitable for local reviewer rejection UI testing.

Guardrails:

- `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` is required; without it, the script fails closed.
- The script fails closed if configured URL, URI, origin, host, domain, or base environment variables point to `access2.salvardata.com`, `api.salvardata.com`, `railway.app`, or `up.railway.app`.
- Do not run this script against Railway, production, or shared seeded demo data.
- The marker is separate from `access2-railway-demo:*`; the four Railway demo patients remain unchanged.
- Demo Patient 3 remains the production read-only rejected-posture scenario and should not be reused for repeatable mutation E2E.
- After a prior local rejection, rerunning the script creates a new latest `pending_review` snapshot instead of rewriting the rejected terminal snapshot.
- No production Playwright mutation test is enabled; local mutation E2E must target this disposable marker/patient only.
- Non-goals remain: no real PHI, no production mutation E2E, no Railway seed change, no deployment config change, no override approval UI, and no audit-readiness queue mutation controls.

When the local backend, local frontend, and disposable local seed are ready, run the gated local mutation spec only against localhost:

```powershell
cd C:\dev\access2\frontend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:ACCESS2_E2E_BASE_URL="http://localhost:3001"
$env:ACCESS2_E2E_API_BASE_URL="http://localhost:8000/api/v1"
$env:ACCESS2_E2E_ADMIN_EMAIL="admin@example.com"
$env:ACCESS2_E2E_ADMIN_PASSWORD="Admin123!"
$env:ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID="<value printed by seed script>"
npm run test:e2e:local-mutation
```

The local mutation spec is separate from the production Railway demo spec. It skips unless `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` is set and fails closed if the configured frontend or API target contains `access2.salvardata.com`, `api.salvardata.com`, `railway.app`, or `up.railway.app`.

Latest local validation:

- `npm run test:e2e:local-mutation` passed against localhost only with `1 passed (2.2m)` on `http://localhost:3001`.
- This confirmed the disposable local patient/snapshot setup supports the V2 correction loop: latest rejected snapshot -> create new immutable review packet snapshot -> new latest `pending_review` snapshot.
- The old rejected snapshot remained visible/read-only with persisted packet content preserved.
- Assignment and rejection controls appeared only for the latest `pending_review` snapshot and were absent from the rejected historical snapshot.
- Reviewer Work Queue remained read-only with no approve, reject, assign, override, export, or create-snapshot mutation controls.
- The local-only guardrails allowed safe mutation validation without touching shared production demo data.
- A prior attempted run against `https://access2.salvardata.com` was refused as expected, confirming the production/Railway target guard.
- Demo Patient 3 remains the production read-only rejected-posture scenario, the existing production `Demo Patient 3 reviewer rejection through UI` test remains skipped, and Railway production E2E remains read-only.
- Non-goals remain unchanged: no production mutation E2E activation, no shared demo data mutation, no Railway/deployment config change, no override approval UI, and no audit-readiness queue mutation controls.
- See [access2-v2-correction-loop-demo.md](C:/dev/access2/docs/access2-v2-correction-loop-demo.md) for the manual V2 local-only demo script.

### 5. Approve The Snapshot

Use normal approval when the packet is ready:

```powershell
Invoke-RestMethod `
  -Method Patch `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/review" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    review_status = "approved"
    review_note = "Evidence validated and approved."
  } | ConvertTo-Json)
```

If approval is blocked because the local demo snapshot has missing checklist items, the documented superuser override path may be used for local demo data only:

```powershell
Invoke-RestMethod `
  -Method Patch `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/review" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    review_status = "approved"
    decision_note = "Approved under documented exception."
    override_missing_checklist = $true
    override_reason = "Time-sensitive payer submission with documented missing closure evidence."
  } | ConvertTo-Json)
```

Expected result:

- Snapshot review status becomes `approved`.
- Immutable packet content remains unchanged.
- Override approval is documented in the review state when used.

### 6. Export Bundles And Capture The Manifest

Export the JSON bundle first because it contains the `audit_manifest` needed for verification:

```powershell
$Bundle = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle" `
  -Headers $Headers
```

Then export Markdown and PDF:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/markdown" `
  -Headers $Headers

Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/pdf" `
  -Headers $Headers `
  -OutFile "access-review-packet-audit-bundle-$SNAPSHOT_ID.pdf"
```

Expected result:

- JSON export includes `$Bundle.audit_manifest`.
- JSON, Markdown, and PDF exports succeed only for approved snapshots.
- Successful exports may record `audit_bundle_exported` events.

### 7. Verify The Manifest

Backend verification:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/verify" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    audit_manifest = $Bundle.audit_manifest
  } | ConvertTo-Json -Depth 6)
```

Frontend verification:

1. Open `http://localhost:3001/audit-bundle-verify`.
2. Paste `$SNAPSHOT_ID` into `Snapshot ID`.
3. Paste only the JSON `audit_manifest` object into `Audit manifest JSON`.
4. Select `Verify Manifest`.

Expected result:

- The frontend result says `Verified`.
- Mismatch, invalid JSON, missing-field, auth, and backend error states remain understandable if deliberately tested.

### 8. Confirm Audit Readiness

Check latest-per-patient audit readiness again:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BackendBase/reports/access-review-packet/audit-readiness" `
  -Headers $Headers
```

Expected result:

- At least one latest-snapshot row exists.
- The selected row shows an approved/export-ready or `audit_ready` posture.
- `audit_bundle.available` is `true`.
- `audit_bundle.exported` is `true` after a successful export.
- Export formats include `json`, `markdown`, and `pdf` after all three exports.

## Evidence To Capture

Record these values for the demo handoff:

- Patient ID
- Snapshot ID
- Completion status
- Review status
- Review state
- Audit bundle available/exported
- Export formats
- Verification result

## Troubleshooting

- Docker/backend not reachable: start Docker Desktop, run `docker compose ps`, and confirm `/health/ready` returns HTTP 200.
- Login page loads but sign-in fails: confirm backend health, frontend API base URL, and seeded auth.
- No patients: run the existing guarded Selenium bootstrap path against a disposable local database.
- No snapshots: use the existing operator-flow snapshot creation step.
- Snapshot is `blocked_missing_evidence`: approve normally only if evidence is ready; for local demo data only, use the documented override path with a reason.
- Rejection mutation test needs a `pending_review` snapshot: use a disposable local patient or a documented reset/reseed flow. Shared production demo data must remain stable for demos.
- No approved export-ready snapshot: complete approval first, then export the JSON bundle.
- JSON download works but verification fails: confirm you copied only the `audit_manifest` object from the matching snapshot bundle.
- Invalid JSON: recopy the manifest object including opening and closing braces.
- Markdown/PDF unavailable: confirm the snapshot is approved and export-ready.
- Local pytest/cache warnings: treat `backend/.tmp/pytest_cache` or `.pytest_cache` permission warnings as environmental unless they block commands.

## Success Criteria

The demo data is ready when:

- `Audit Readiness` shows at least one latest-snapshot row.
- Patient detail opens from the audit-readiness row.
- Patient audit-status panel shows an export-ready or audit-ready state.
- Review-packet backlog shows an approved snapshot with JSON, Markdown, and PDF download actions.
- JSON audit bundle contains a real `audit_manifest`.
- The manifest verifies successfully.
- The documented frontend demo script can proceed end to end.

## Commit Hygiene

Do not commit:

```text
frontend/.env.local
frontend/tsconfig.tsbuildinfo
backend/.tmp/pytest_cache
```

If this remains a docs-only slice, commit only this checklist.
