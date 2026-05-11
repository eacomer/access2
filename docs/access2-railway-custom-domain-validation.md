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

& 'C:\Program Files\nodejs\npm.cmd' run test:e2e
```

Expected result:

- 8 passed
- 2 skipped
- 0 failed

The skipped tests are expected because ACCESS2 V1 frontend audit panels are read-only:

- Demo Patient 3 reviewer rejection through UI
- Demo Patient 4 superuser override approval through UI

## Production E2E Troubleshooting

Use this triage path when the production E2E result is not `8 passed, 2 skipped, 0 failed`.

1. Confirm the backend custom domain is healthy before interpreting UI failures:

   ```powershell
   Invoke-RestMethod "https://api.salvardata.com/api/v1/health/live"
   Invoke-RestMethod "https://api.salvardata.com/api/v1/health/ready"
   ```

   Expected: `status=ok`, `database=ok`, and `redis=ok`. If readiness fails, treat it as a production environment issue before changing product code.

2. If Playwright fails with `browserType.launch: spawn EPERM`, rerun from an environment that can launch Chromium. This is local execution friction, not an ACCESS2 product failure.

3. If login fails, verify:

   - `ACCESS2_E2E_BASE_URL` is `https://access2.salvardata.com`.
   - `ACCESS2_E2E_ADMIN_EMAIL` and `ACCESS2_E2E_ADMIN_PASSWORD` use synthetic demo credentials only.
   - The frontend `NEXT_PUBLIC_API_BASE_URL` still points to `https://api.salvardata.com/api/v1`.
   - Backend `FRONTEND_ORIGIN` still points to `https://access2.salvardata.com`.

4. If seeded patient tests skip or cannot find data, confirm the four `ACCESS2_E2E_DEMO_PATIENT_*_ID` values match the seeded synthetic IDs in this document. Do not enter real PHI or reseed production with ad hoc startup commands.

5. If `/demo/release-summary` assertions fail, confirm the deployed frontend includes the Demo Release Summary Evidence Proof Checklist and shows the `8 passed`, `2 skipped`, `0 failed` baseline. A failure here usually means the custom domain is serving an older deployment.

6. If Reviewer Work Queue or patient-detail assertions fail, check whether the page still presents read-only posture only. Do not add approve, reject, override, assign, export, or create-snapshot controls to satisfy production E2E.

7. After each E2E run, remove generated Playwright artifacts before reviewing git state:

   ```powershell
   cd C:\dev\access2

   Remove-Item -Recurse -Force frontend\playwright-report -ErrorAction SilentlyContinue
   Remove-Item -Recurse -Force frontend\test-results -ErrorAction SilentlyContinue

   git status --short
   ```

## Latest Production Custom-Domain Validation

Latest production custom-domain E2E validation confirmed the deployed frontend login works, the Demo Guide page is protected and visible after login, the Demo Release Summary includes the read-only Evidence Proof Checklist, and the deployed patient detail page shows the Evidence Chain, Manifest Verification, and Outcome Proof Gaps panels for all four seeded synthetic demo patients. Outcome Proof Gaps now renders backend-owned audit-status `readiness_reasons` for the patient proof-gap explanation.

Result:

- 8 passed
- 2 skipped
- 0 failed

Validated production demo baseline:

- Deployed login works.
- Demo Guide coverage is included.
- Demo Guide validates the proof chain, four seeded patient scenario links, Evidence Chain explanation, Manifest Verification explanation, and synthetic/no-PHI safety text.
- Demo Release Summary coverage is included.
- Demo Release Summary validates the read-only Evidence Proof Checklist for:
  - Demo Patient 1 - Audit Ready: `f4c31931-8fc2-41d6-9f45-9ab0bd039088`
  - Demo Patient 2 - Missing Evidence: `1c5c7db8-96f8-47af-a643-741641ecdcf3`
  - Demo Patient 3 - Rejected Review: `4c1ef5ef-1216-453d-b317-b965a0dd1dea`
  - Demo Patient 4 - Override Approval: `2e9dc25c-2e56-4d6a-aea0-8706d33b0444`
- The checklist makes this ACCESS2 evidence chain explicit:

  ```text
  signal → escalation → intervention → outcome → evidence → case summary → immutable review packet snapshot → approval/rejection → audit bundle → manifest verification
  ```

- The checklist includes signal, escalation, intervention, outcome, evidence, case summary, immutable review packet snapshot, review posture, audit bundle availability/export status, manifest verification, readiness reasons, and next step.
- Seeded synthetic demo patients are reachable.
- Evidence Chain panel is visible and validated for all four seeded demo patients.
- Manifest Verification panel is visible and validated for all four seeded demo patients.
- Outcome Proof Gaps panel is visible and validated for all four seeded demo patients.
- Outcome Proof Gaps assertions validate backend-owned `readiness_reasons` rendered from the audit-status response, including `code`, `severity`, `label`, and `detail` reason text.
- Demo Patient 1 - Audit Ready validates authenticated frontend proxy downloads for JSON, Markdown, and PDF audit bundles.
- JSON audit bundle download validation confirms persisted `readiness_reasons` are present with `code`, `severity`, `label`, and `detail`.
- Markdown audit bundle download validation confirms the `Audit Readiness Reasons` section is present.
- PDF audit bundle download validation confirms non-empty PDF output.
- Outcome Proof Gaps reinforces the evidence chain:

  ```text
  signal → escalation → intervention → outcome → evidence → case summary → immutable review packet snapshot → approval/rejection → audit bundle → manifest verification
  ```

- Missing-evidence posture is validated.
- Audit-ready/export posture is validated.
- Rejected-review posture is validated.
- Override-approval posture is validated.
- Read-only page and panel expectations remain valid.

The skipped tests remain expected because ACCESS2 V1 exposes the reviewer rejection and superuser override approval states as read-only seeded demo postures rather than frontend mutation workflows.

Manifest Verification panel validation confirms the visible read-only verification posture shown by the deployed UI. It does not change workflow state, create exports, approve or reject snapshots, or imply real CMS submission.

Outcome Proof Gaps validation confirms the visible read-only explanation of why each seeded patient is or is not audit-ready. The panel is driven by backend `readiness_reasons` from the patient audit-status response so the deployed UI does not infer the core proof-gap reasons only from scattered page data. It does not change workflow state, create snapshots, approve or reject snapshots, export bundles, or imply real CMS submission.

## Production Operator Smoke Checklist

Use this lightweight human smoke check after a production deploy, custom-domain change, or demo reset. This checklist is read-only and uses synthetic/demo data only.

1. Open the production frontend:

   ```text
   https://access2.salvardata.com
   ```

2. Log in with synthetic demo credentials only:

   ```text
   admin@example.com / Admin123!
   demo@example.com / Secret123!
   ```

3. Confirm the `Demo Guide` link is reachable from the app navigation.

4. On the Demo Guide page, confirm it explains:

   - `signal → escalation → intervention → outcome → evidence → case summary → immutable review packet snapshot → approval/rejection → audit bundle → manifest verification`
   - Synthetic/demo-only safety expectations.
   - No real PHI should be entered.

5. Open `Release Summary` and confirm the read-only Evidence Proof Checklist covers all four seeded synthetic demo patients and shows the signal-to-verification evidence chain, readiness reasons, and next step without mutation controls.

6. Open each seeded synthetic demo patient from the app:

   - Demo Patient 1 - Audit Ready: `f4c31931-8fc2-41d6-9f45-9ab0bd039088`
   - Demo Patient 2 - Missing Evidence: `1c5c7db8-96f8-47af-a643-741641ecdcf3`
   - Demo Patient 3 - Rejected Review: `4c1ef5ef-1216-453d-b317-b965a0dd1dea`
   - Demo Patient 4 - Override Approval: `2e9dc25c-2e56-4d6a-aea0-8706d33b0444`

7. For each patient, confirm these read-only proof panels are visible:

   - Patient audit posture/status.
   - Evidence Chain.
   - Manifest Verification.
   - Outcome Proof Gaps, backed by backend audit-status `readiness_reasons`.

8. For Demo Patient 1 - Audit Ready, confirm approved/export-ready audit bundle download actions are available for:

   - JSON audit bundle.
   - Markdown audit bundle.
   - PDF audit bundle.

   Automated E2E coverage validates these downloads through the authenticated frontend proxy. JSON is checked for persisted `readiness_reasons` with `code`, `severity`, `label`, and `detail`; Markdown is checked for the `Audit Readiness Reasons` section; PDF is checked as non-empty PDF output.

9. Confirm ACCESS2 V1 does not expose frontend mutation controls for:

   - Demo Patient 3 reviewer rejection through UI.
   - Demo Patient 4 superuser override approval through UI.

10. If automated confirmation is needed, run the production E2E command in this document using the existing `ACCESS2_E2E_*` environment variable pattern.

Expected production E2E result:

- 8 passed
- 2 skipped
- 0 failed

The skipped tests remain expected because reviewer rejection and superuser override approval are not exposed as frontend mutation controls in ACCESS2 V1.

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
