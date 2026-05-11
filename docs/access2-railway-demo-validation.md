Railway frontend URL
Railway backend URL
Custom domain targets
Required Railway variables
Backend startup command
Seeded demo users
Seeded demo patient IDs
E2E command
Expected production E2E result after Release Summary Evidence Proof Checklist deployment: 8 passed, 2 skipped, 0 failed
Demo Guide coverage
Demo Release Summary Evidence Proof Checklist coverage
Reason for skipped tests
Security reminder to rotate Railway public Postgres credentials

Custom domain validation:

Frontend:
https://access2.salvardata.com

Backend API:
https://api.salvardata.com/api/v1

Backend FRONTEND_ORIGIN:
https://access2.salvardata.com

E2E result before Reviewer Work Queue expansion:
7 passed, 2 skipped, 0 failed

Expected E2E result after Reviewer Work Queue deployment:
8 passed, 2 skipped, 0 failed

Expected E2E result after Release Summary Evidence Proof Checklist deployment:
8 passed, 2 skipped, 0 failed

Demo Guide coverage:
- Protected Demo Guide page opens after login.
- Proof chain text is present.
- Four seeded patient scenario links are present.
- Evidence Chain explanation is present.
- Manifest Verification explanation is present.
- Synthetic/no-PHI safety text is present.

Production E2E baseline:
- Frontend: https://access2.salvardata.com
- Backend API: https://api.salvardata.com/api/v1
- Latest result: 8 passed, 2 skipped, 0 failed
- Fresh production validation on 2026-05-11 returned 8 passed, 2 skipped, 0 failed against https://access2.salvardata.com.
- One earlier transient login-helper assertion failure was resolved by rerun and did not indicate a production auth outage.
- Validates login.
- Validates Demo Guide.
- Validates the protected `/demo/release-summary` page.
- Validates the protected Reviewer Work Queue at `/audit-readiness`.
- Validates four seeded demo patient scenarios.
- Validates Evidence Chain panel assertions.
- Validates Manifest Verification panel assertions.
- Validates Outcome Proof Gaps panel assertions backed by backend audit-status `readiness_reasons`.
- Validates authenticated frontend proxy downloads for JSON, Markdown, and PDF audit bundles using Demo Patient 1 - Audit Ready.
- Validates JSON audit bundle `readiness_reasons` shape: `code`, `severity`, `label`, and `detail`.
- Validates Markdown audit bundle output includes `Audit Readiness Reasons`.
- Validates PDF audit bundle output is non-empty PDF content.

Production E2E command:

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

Cleanup after production E2E:

```powershell
cd C:\dev\access2

Remove-Item -Recurse -Force frontend\playwright-report -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force frontend\test-results -ErrorAction SilentlyContinue

git status --short
```

Reviewer Work Queue:
- Protected frontend route: `/audit-readiness`
- Navigation label: `Reviewer Queue`
- Purpose: a read-only reviewer/operator queue for seeing latest review-packet posture across audit-ready, missing-evidence/blocked, rejected-review, override-approval, pending/needs-review, and exported-bundle states.
- Uses existing backend endpoints:
  - `GET /reports/access-review-packet/audit-readiness`
  - `GET /reports/access-review-packet/snapshots/queue-summary`
  - `GET /reports/access-review-packet/reviewer/my-summary`
- Links queue rows to patient detail through safe synthetic patient identifiers.
- Does not approve, reject, override, assign, export, create snapshots, or mutate workflow state in V1.
- Strengthens the ACCESS2 evidence chain by helping reviewers move from organization-level packet posture to patient-level proof without changing persisted audit artifacts:

```text
signal → escalation → intervention → outcome → evidence → case summary → immutable review packet snapshot → approval/rejection → audit bundle → manifest verification
```

Demo release summary:
- Protected frontend route: `/demo/release-summary`
- Purpose: one read-only operator/reviewer page for the current ACCESS2 V1 production/demo release posture.
- Summarizes the production frontend URL, frontend-configured backend API base URL, Demo Guide availability, four seeded demo patient scenarios, expected operator messages, and the known production E2E baseline.
- Includes a read-only `Evidence Proof Checklist` that makes the ACCESS2 evidence chain explicit:

```text
signal → escalation → intervention → outcome → evidence → case summary → immutable review packet snapshot → approval/rejection → audit bundle → manifest verification
```

- The checklist covers all four seeded synthetic demo patients:
  - Demo Patient 1 - Audit Ready: `f4c31931-8fc2-41d6-9f45-9ab0bd039088`
  - Demo Patient 2 - Missing Evidence: `1c5c7db8-96f8-47af-a643-741641ecdcf3`
  - Demo Patient 3 - Rejected Review: `4c1ef5ef-1216-453d-b317-b965a0dd1dea`
  - Demo Patient 4 - Override Approval: `2e9dc25c-2e56-4d6a-aea0-8706d33b0444`
- The checklist shows read-only rows for signal, escalation, intervention, outcome, evidence, case summary, immutable review packet snapshot, review posture, audit bundle availability/export status, manifest verification, readiness reasons, and next step.
- Production E2E directly validates the page heading, seeded scenario postures, Evidence Proof Checklist copy, baseline values, and expected V1 read-only skip rationale.
- Records the expected skipped tests as V1 read-only constraints: no reviewer rejection mutation control and no superuser override approval mutation control in the frontend.
- Does not create workflow state, export bundles, approve or reject snapshots, or add mutation controls.

Readiness reason evidence:
- `readiness_reasons` are backend-owned structured reason codes with `code`, `severity`, `label`, and `detail`.
- The backend persists `readiness_reasons` into snapshot, review, and audit-bundle export event metadata.
- Audit bundle JSON exposes `readiness_reasons` from persisted event metadata rather than recomputing from live patient state.
- Audit bundle Markdown includes an `Audit Readiness Reasons` section with the persisted reason-code basis.
- Audit bundle PDF includes the same section because it renders from the Markdown audit bundle payload.
- Snapshot `packet_json` and `packet_markdown` remain immutable.
- This preserves the ACCESS2 evidence chain by carrying the reason-code basis forward into both machine-readable and human-readable evidence/export records:

```text
signal → escalation → intervention → outcome → evidence → case summary → immutable review packet snapshot → approval/rejection → audit bundle → manifest verification
```

Outcome Proof Gaps coverage:
- The panel is visible on all four seeded patient detail pages.
- The panel now prefers backend-owned `readiness_reasons` from the patient audit-status response.
- E2E assertions validate rendered reason `severity`, `label`, and `detail` text for audit-ready, missing-evidence, rejected-review, and override-approval seeded patients.
- The panel reinforces the ACCESS2 evidence chain:

```text
signal → escalation → intervention → outcome → evidence → case summary → immutable review packet snapshot → approval/rejection → audit bundle → manifest verification
```

- Demo Patient 1 - Audit Ready shows satisfied proof elements and audit-readiness support.
- Demo Patient 2 - Missing Evidence shows missing or partial outcome proof gaps and explains why audit readiness is incomplete.
- Demo Patient 3 - Rejected Review shows the proof packet/snapshot exists and the review posture is rejected.
- Demo Patient 4 - Override Approval shows the override/superuser review posture.

Expected skips:
- Demo Patient 3 reviewer rejection through UI
- Demo Patient 4 superuser override approval through UI

Reason:
ACCESS2 V2 now supports controlled reviewer rejection through the patient detail page for the latest `pending_review` snapshot only, routed through a reject-only frontend proxy and the existing backend review endpoint. Production mutation E2E remains skipped because shared seeded demo data must stay stable for demos, and Demo Patient 3 is already seeded as rejected rather than pending review.

The skipped `Demo Patient 3 reviewer rejection through UI` test must remain skipped until there is a safe reset/reseed strategy or a local-only disposable pending-review patient for mutation E2E. The Demo Patient 4 superuser override approval path also remains skipped because override approval UI is not part of the controlled rejection rollout.

A separate local-only seed/reset script exists for future local mutation E2E: `backend/scripts/seed_local_v2_rejection_mutation.py`. It uses marker `access2-local-v2-mutation:reviewer-rejection`, requires `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true`, and must not be run against Railway, production, or shared seeded demo data.

Do not run production mutation E2E against shared seeded demo data until reset/reseed steps are documented.

Security cleanup:

The Railway Postgres password/connection string was rotated after troubleshooting.
The backend DATABASE_URL now uses the Railway internal Postgres host:
postgres.railway.internal:5432/railway

Post-rotation validation:
- Backend /health/live returned ok.
- Backend /health/ready returned ok with database=ok and redis=ok.
- Latest E2E against https://access2.salvardata.com returned 8 passed, 2 skipped, 0 failed.
