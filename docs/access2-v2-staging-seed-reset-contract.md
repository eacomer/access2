# ACCESS2 V2 Staging Seed/Reset Contract

## Purpose

This is a contract and specification document only. It defines the requirements a future isolated staging seed/reset process must satisfy before ACCESS2 V2 mutation testing can move beyond localhost.

This document is not permission to run mutation tests outside localhost, and it does not approve a staging seed script, staging E2E run, production mutation E2E run, or production demo-data mutation.

## Environment Boundary

The future seed/reset process must target only an isolated staging or preview environment.

It must never target:

- `https://access2.salvardata.com`
- `https://api.salvardata.com/api/v1`
- Railway production targets on `railway.app`
- Railway production targets on `up.railway.app`

The process must fail closed when the target frontend URL, backend API URL, database identity, or database label is missing, unknown, or production-like. A missing safety signal is a refusal condition, not a prompt to continue.

## Data Boundary

The future staging data set must be synthetic only.

Required data boundaries:

- No real PHI.
- No imported production database dumps.
- No shared production demo patient IDs.
- No reuse of `access2-railway-demo:*` production demo markers for mutation testing.
- Seeded patients, users, evidence, snapshots, and audit records must be clearly marked as staging and synthetic.
- Staging mutation data must be disposable without affecting production or shared production demo posture.

## Required Scenario

The future staging seed/reset process must create or restore one disposable corrected-packet scenario that can prove the full local V2 correction-loop posture in staging:

- The latest `pending_review` snapshot can be assigned.
- A `pending_review` snapshot can be rejected with a non-empty decision note.
- The rejected snapshot remains immutable historical audit evidence.
- Corrected evidence and corrected outcome posture can be created.
- A new `pending_review` snapshot can be created from corrected evidence.
- The corrected latest `pending_review` snapshot can be approved.
- The approved snapshot becomes terminal and read-only.
- Historical rejected and approved snapshots remain read-only.

The scenario must continue to support the ACCESS2 product principle that interventions led to measurable outcomes, not only that events occurred.

## Idempotency Requirements

Re-running the future staging seed/reset process must produce a known baseline.

Required rerun behavior:

- It must not rewrite old terminal `packet_json` or `packet_markdown`.
- It must not mutate rejected, approved, or override-approved terminal review history.
- It must either clean the disposable staging scenario safely or create a new clearly marked latest `pending_review` snapshot.
- It must avoid accumulating ambiguous duplicate active mutation scenarios.
- It must make the expected next E2E starting point obvious to the operator.

## Tenant And User Requirements

The future seed/reset process must preserve tenant scoping and patient consistency.

Required tenant and user rules:

- Use staging-only demo, admin, and reviewer users.
- Do not reuse production credentials.
- Do not print or commit credentials.
- Seed reviewer-assignment prerequisites if the staging E2E flow needs them.
- Clearly document which user roles are required for setup and E2E execution.
- Keep staging mutation users separate from shared production demo users unless a later implementation explicitly proves safe isolation.

## Audit/Evidence Requirements

The seeded scenario must preserve the ACCESS2 proof chain:

```text
signal -> escalation -> intervention -> outcome -> evidence -> case summary -> immutable review packet snapshot -> assignment -> approval/rejection -> audit bundle -> manifest verification
```

Required audit behavior:

- Rejection events must remain auditable.
- Approval events must remain auditable.
- New snapshots must be created from current corrected evidence.
- Old snapshots must remain historical audit evidence.
- Rejected snapshots must not become export-ready audit bundles.
- Approved corrected snapshots must become terminal/read-only and audit-bundle-ready.
- Manifest verification expectations must remain tied to persisted snapshot data.

## Required Outputs

The future script should print only non-secret values needed by staging E2E or operator handoff.

Allowed output examples:

- Staging marker.
- Staging synthetic patient ID.
- Latest pending snapshot ID, if useful.
- Reviewer or admin user identifiers only when non-sensitive and needed.
- Target frontend/backend labels.

Forbidden output examples:

- Passwords.
- Tokens.
- Database URLs.
- Secret store values.
- Full connection strings.
- Any credential material.

## Safety Checks

The future script must:

- Require an explicit staging mutation flag.
- Verify the target frontend and backend hosts are not production-like.
- Verify the database identity or label is staging-like when a safe check exists.
- Refuse unknown, missing, or ambiguous targets.
- Refuse `access2.salvardata.com`, `api.salvardata.com`, `railway.app`, and `up.railway.app` targets unless a future implementation has a stricter non-production allowlist that proves the target is isolated staging.
- Clearly log refusal reasons without exposing secrets.

The refusal path is part of the contract. A failure to prove safety must stop the run.

## Dry-Run Contract Check

`backend/scripts/check_staging_v2_seed_reset_contract.py` is a dry-run-only input validation check for future staging seed/reset work. It does not seed or reset data, does not connect to a database, and does not make network calls.

The check requires all of these non-secret environment variables before it exits successfully:

```text
ACCESS2_STAGING_SEED_RESET_DRY_RUN=true
ACCESS2_ENABLE_STAGING_MUTATION_DRY_RUN=true
ACCESS2_STAGING_FRONTEND_URL=<isolated staging or preview frontend URL>
ACCESS2_STAGING_API_BASE_URL=<isolated staging or preview API URL>
ACCESS2_STAGING_ENV_LABEL=<staging-or-preview-like label>
ACCESS2_STAGING_DATA_CLASSIFICATION=synthetic
```

The check refuses production/custom-domain and Railway-like targets, credential-bearing URLs, query strings, non-synthetic data classification, and production-like environment labels. Localhost is refused unless `ACCESS2_ALLOW_LOCAL_STAGING_DRY_RUN=true` is set for local validation of the check itself.

This dry-run check is not permission to run staging mutation E2E. A real staging seed/reset still requires an isolated database, a reviewed seed/reset implementation, completed staging checklist, synthetic-only data, and explicit approval. Production remains read-only.

## Reset And Rollback Expectations

A failed staging seed/reset or mutation E2E run must have a documented cleanup path.

Required rollback behavior:

- Staging can be returned to a known synthetic baseline.
- Cleanup must not touch production.
- Cleanup must not touch shared production demo data.
- Terminal historical snapshots should remain immutable unless the entire disposable staging scenario is safely dropped or reset inside an isolated staging database.
- Partial runs must not leave an ambiguous latest active mutation target.

## E2E Handoff Expectations

The future staging seed/reset process should provide the non-secret values a staging mutation E2E needs, including:

- Staging frontend base URL label.
- Staging backend API base URL label.
- Synthetic staging patient ID.
- Latest pending snapshot ID, if the E2E spec chooses to target a snapshot directly.
- Reviewer/admin user identifiers only when non-sensitive and needed by the E2E flow.
- Marker showing the scenario is the staging V2 correction-loop mutation scenario.

Mutation E2E must remain separate from production read-only E2E. The current localhost mutation E2E remains the only approved mutation E2E until staging implementation is explicitly approved.

## Relationship To Existing Scripts

`backend/scripts/seed_local_v2_rejection_mutation.py` is the closest existing seed/reset model for the future staging contract. Based on inspection, it is localhost-oriented:

- It requires `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true`.
- It uses the disposable marker `access2-local-v2-mutation:reviewer-rejection`.
- It restores a latest `pending_review` snapshot after a prior local rejection by creating a new snapshot rather than rewriting the rejected terminal snapshot.
- It refuses configured URL/domain/base/origin environment variables containing production-like host markers.
- It prints only `ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID`.

The future staging script may reuse the same safety principles, but it should not silently reuse the local gate name or local marker unless the implementation explicitly decides that is the correct staging contract.

`backend/scripts/seed_railway_demo_cases.py` is a separate synthetic Railway demo seeder. Based on inspection, it creates or repairs four stable demo patients marked with `access2-railway-demo:*`, establishes read-only demo postures, records audit-bundle evidence for approved demo cases, and prints demo patient IDs for E2E configuration.

Railway production demo seeding must not be repurposed for staging mutation testing. The future staging mutation seed/reset process needs its own isolated markers, isolated database, isolated users, and explicit reset/rollback semantics.

## Explicit Non-Goals

- No staging seed/reset implementation in this slice.
- No production seed/reset mutation.
- No production mutation E2E.
- No shared production demo-data mutation.
- No superuser override approval implementation.
- No broad workflow mutation controls.
- No Railway config changes.
- No backend behavior changes.
- No frontend behavior changes.
- No E2E code changes.

## Open Questions Before Implementation

- What is the exact staging environment name and frontend URL?
- What is the exact staging backend API URL?
- What database identity or label can the seed/reset process verify safely?
- Will staging run on Railway preview, a separate Railway service set, or another host?
- Should staging use a new staging-only mutation gate variable, or extend the local mutation gate with stricter target classification?
- Should staging seed/reset clean disposable scenarios or version them with new latest snapshots?
- Which staging-only user roles should be seeded for assignment and approval?
- What validation artifacts should operators record after a staging mutation run?
