# ACCESS2 Railway Custom-Domain Production Demo Validation

## Purpose

This document validates the current Railway custom-domain production demo baseline for ACCESS2.

Use it to repeat the known-good production validation after deployment, credential rotation, domain changes, or demo reset work.

## Scope

- Documentation and checklist only.
- Synthetic/demo data only.
- No real PHI.
- No secrets.
- No application behavior changes.
- No seed command should be left as a Railway startup command.

## Known-Good Production URLs

- Production frontend: https://access2.salvardata.com
- Production backend API base: https://api.salvardata.com/api/v1
- Railway backend URL: https://access2-backend-production-881f.up.railway.app
- Railway frontend URL: https://access2-frontend-production-c029.up.railway.app

## Expected Railway Environment Configuration

- Backend `FRONTEND_ORIGIN` should be `https://access2.salvardata.com`.
- Frontend `NEXT_PUBLIC_API_BASE_URL` should be `https://api.salvardata.com/api/v1`.
- Backend startup command should remain `bash scripts/render-start.sh`.
- Backend `DATABASE_URL` should use the Railway internal Postgres host `postgres.railway.internal:5432/railway`.
- Do not document the full `DATABASE_URL`, database password, tokens, or Railway secret values.
- Do not leave seed commands as Railway startup commands.

## Postgres Credential Rotation Validation

Railway Postgres credentials were rotated after accidental exposure during troubleshooting.

Post-rotation validation passed:

- `/health/live` returned `status=ok`.
- `/health/ready` returned `status=ok`.
- `/health/ready` returned `database=ok`.
- `/health/ready` returned `redis=ok`.

Do not include actual secret values in this document, commits, screenshots, issues, or pull requests.

## Health Check Commands

Run from PowerShell:

```powershell
cd C:\dev\access2

Invoke-RestMethod "https://api.salvardata.com/api/v1/health/live"
Invoke-RestMethod "https://api.salvardata.com/api/v1/health/ready"
```

Expected result:

- Live status: `ok`
- Ready status: `ok`
- Database: `ok`
- Redis: `ok`

## Seeded Users

These are synthetic demo credentials only:

- `admin@example.com` / `Admin123!`
- `demo@example.com` / `Secret123!`

## Seeded Synthetic Demo Patients

- Demo Patient 1 - Audit Ready: `f4c31931-8fc2-41d6-9f45-9ab0bd039088`
- Demo Patient 2 - Missing Evidence: `1c5c7db8-96f8-47af-a643-741641ecdcf3`
- Demo Patient 3 - Rejected Review: `4c1ef5ef-1216-453d-b317-b965a0dd1dea`
- Demo Patient 4 - Override Approval: `2e9dc25c-2e56-4d6a-aea0-8706d33b0444`

## E2E Production Validation Command

Run from PowerShell:

```powershell
cd C:\dev\access2\frontend

$env:ACCESS2_E2E_BASE_URL="https://access2.salvardata.com"
$env:ACCESS2_E2E_ADMIN_EMAIL="admin@example.com"
$env:ACCESS2_E2E_ADMIN_PASSWORD="Admin123!"

$env:ACCESS2_E2E_DEMO_PATIENT_1_ID="f4c31931-8fc2-41d6-9f45-9ab0bd039088"
$env:ACCESS2_E2E_DEMO_PATIENT_2_ID="1c5c7db8-96f8-47af-a643-741641ecdcf3"
$env:ACCESS2_E2E_DEMO_PATIENT_3_ID="4c1ef5ef-1216-453d-b317-b965a0dd1dea"
$env:ACCESS2_E2E_DEMO_PATIENT_4_ID="2e9dc25c-2e56-4d6a-aea0-8706d33b0444"

npm run test:e2e
```

Expected result:

- 6 passed
- 2 skipped
- 0 failed

The skipped tests are expected because ACCESS2 V1 frontend audit panels are read-only:

- Demo Patient 3 reviewer rejection through UI
- Demo Patient 4 superuser override approval through UI

## Latest Production Custom-Domain Validation

Latest production custom-domain E2E validation confirmed the deployed frontend login works, the Demo Guide page is protected and visible after login, and the deployed patient detail page shows both the Evidence Chain panel and the Manifest Verification panel for all four seeded synthetic demo patients.

Result:

- 6 passed
- 2 skipped
- 0 failed

Validated production demo baseline:

- Deployed login works.
- Demo Guide coverage is included.
- Demo Guide validates the proof chain, four seeded patient scenario links, Evidence Chain explanation, Manifest Verification explanation, and synthetic/no-PHI safety text.
- Seeded synthetic demo patients are reachable.
- Evidence Chain panel is visible and validated for all four seeded demo patients.
- Manifest Verification panel is visible and validated for all four seeded demo patients.
- Missing-evidence posture is validated.
- Audit-ready/export posture is validated.
- Rejected-review posture is validated.
- Override-approval posture is validated.
- Read-only page and panel expectations remain valid.

The skipped tests remain expected because ACCESS2 V1 exposes the reviewer rejection and superuser override approval states as read-only seeded demo postures rather than frontend mutation workflows.

Manifest Verification panel validation confirms the visible read-only verification posture shown by the deployed UI. It does not change workflow state, create exports, approve or reject snapshots, or imply real CMS submission.

## Playwright Cleanup Commands

Run from PowerShell after E2E validation:

```powershell
cd C:\dev\access2

Remove-Item -Recurse -Force frontend\playwright-report -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force frontend\test-results -ErrorAction SilentlyContinue

git status --short
```

## Git Hygiene

- Do not commit generated Playwright artifacts.
- Do not commit secrets.
- Review the docs diff before committing.

Run from PowerShell:

```powershell
cd C:\dev\access2
git status --short
git diff -- docs
git add docs
git commit -m "Document Railway custom domain validation baseline"
git status --short
```

## Definition of Done

- This document exists or the existing custom-domain validation document is updated.
- Custom-domain URLs are included.
- Environment expectations are included without secrets.
- Credential rotation validation summary is included.
- Health check commands are included.
- Seeded demo users and patient IDs are included.
- E2E command and expected result are included.
- Playwright cleanup commands are included.
- Repo is clean after commit except ignored/generated artifacts.
