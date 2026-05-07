# ACCESS2 Railway Demo E2E

This Playwright suite validates the synthetic ACCESS2 Railway demo cases against a deployed frontend and the matching backend API. Use synthetic/demo data only.

## Seed Railway Demo Data

Before running the full Railway suite, seed the four synthetic backend cases once against the Railway backend service:

```bash
python scripts/seed_railway_demo_cases.py
```

Copy the printed patient IDs into the PowerShell test environment variables below. The Railway backend startup command must remain `bash scripts/render-start.sh`; do not permanently switch Railway startup to the seed command.

## Windows PowerShell

```powershell
cd C:\dev\access2\frontend
$env:ACCESS2_E2E_BASE_URL="https://access2.salvardata.com"
$env:ACCESS2_E2E_ADMIN_EMAIL="admin@example.com"
$env:ACCESS2_E2E_ADMIN_PASSWORD="Admin123!"
$env:ACCESS2_E2E_DEMO_PATIENT_1_ID="<printed-patient-1-id>"
$env:ACCESS2_E2E_DEMO_PATIENT_2_ID="<printed-patient-2-id>"
$env:ACCESS2_E2E_DEMO_PATIENT_3_ID="<printed-patient-3-id>"
$env:ACCESS2_E2E_DEMO_PATIENT_4_ID="<printed-patient-4-id>"
npm run test:e2e
```

For the current Railway frontend URL:

```powershell
$env:ACCESS2_E2E_BASE_URL="https://access2-frontend-production-c029.up.railway.app"
```

The suite infers the matching backend API for the known ACCESS2 Railway/custom frontend URLs. Override it when needed:

```powershell
$env:ACCESS2_E2E_API_BASE_URL="https://api.salvardata.com/api/v1"
```

By default, each case looks for `Demo Patient 1` through `Demo Patient 4` by display name, then falls back to the expected audit posture for that case. Pin exact seeded records when needed:

```powershell
$env:ACCESS2_E2E_DEMO_PATIENT_1_ID="<audit-ready-patient-id>"
$env:ACCESS2_E2E_DEMO_PATIENT_2_ID="<missing-evidence-patient-id>"
$env:ACCESS2_E2E_DEMO_PATIENT_3_ID="<rejected-review-patient-id>"
$env:ACCESS2_E2E_DEMO_PATIENT_4_ID="<override-approval-patient-id>"
```

## What It Covers

- Login through the deployed Next.js frontend.
- Demo Patient 2 missing-evidence posture and normal approval blocking when a pending blocked snapshot exists.
- Demo Patient 1 approved audit bundle export and manifest verification.
- Demo Patient 3 rejected snapshot state, rejection reason, immutable packet content, and new-snapshot next step.
- Demo Patient 4 override approval metadata, audit bundle metadata, and manifest verification.

Reviewer rejection and override approval are not performed through the UI because the current V1 frontend keeps audit panels read-only and does not expose those controls. Those mutation paths are verified through existing backend API state and explicitly skipped where UI controls are absent.

Failures retain screenshots, traces, and videos under Playwright's test results output. Open the HTML report with:

```powershell
npx playwright show-report
```
