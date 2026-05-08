Railway frontend URL
Railway backend URL
Custom domain targets
Required Railway variables
Backend startup command
Seeded demo users
Seeded demo patient IDs
E2E command
Expected E2E result: 6 passed, 2 skipped, 0 failed
Demo Guide coverage
Reason for skipped tests
Security reminder to rotate Railway public Postgres credentials

Custom domain validation:

Frontend:
https://access2.salvardata.com

Backend API:
https://api.salvardata.com/api/v1

Backend FRONTEND_ORIGIN:
https://access2.salvardata.com

E2E result:
6 passed, 2 skipped, 0 failed

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
- Result: 6 passed, 2 skipped, 0 failed
- Validates login.
- Validates Demo Guide.
- Validates four seeded demo patient scenarios.
- Validates Evidence Chain panel assertions.
- Validates Manifest Verification panel assertions.
- Validates Outcome Proof Gaps panel assertions backed by backend audit-status `readiness_reasons`.

Readiness reason evidence:
- `readiness_reasons` are backend-owned structured reason codes with `code`, `severity`, `label`, and `detail`.
- The backend persists `readiness_reasons` into snapshot, review, and audit-bundle export event metadata.
- Audit bundle JSON exposes `readiness_reasons` from persisted event metadata rather than recomputing from live patient state.
- Snapshot `packet_json` and `packet_markdown` remain immutable.
- This preserves the ACCESS2 evidence chain by carrying the reason-code basis forward into the evidence/export record:

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
ACCESS2 V1 frontend audit panels are read-only; rejection and override approval are intentionally not exposed as frontend mutation controls.
The skipped tests remain expected because ACCESS2 V1 exposes reviewer rejection and superuser override approval as read-only frontend audit postures, not frontend mutation workflows.

Security cleanup:

The Railway Postgres password/connection string was rotated after troubleshooting.
The backend DATABASE_URL now uses the Railway internal Postgres host:
postgres.railway.internal:5432/railway

Post-rotation validation:
- Backend /health/live returned ok.
- Backend /health/ready returned ok with database=ok and redis=ok.
- E2E against https://access2.salvardata.com returned 6 passed, 2 skipped, 0 failed.
