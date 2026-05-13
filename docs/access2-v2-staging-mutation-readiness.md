# ACCESS2 V2 Staging Mutation Readiness

## Purpose

This document defines the readiness bar before ACCESS2 V2 mutation testing moves beyond localhost.

It is a planning document only. It does not authorize production mutation testing, shared demo-data mutation, override approval, Railway configuration changes, backend startup command changes, or broad workflow mutation controls.

## Current Proof And Boundary

The localhost-only V2 correction loop is complete as a controlled proof path:

```text
assignment -> rejection with reason -> immutable rejected packet -> corrected synthetic evidence -> new pending snapshot -> approval -> terminal read-only approved snapshot
```

That proves ACCESS2 can preserve historical review evidence while capturing corrected measurable outcomes in a new immutable packet. It also proves patient-detail-only controls can handle assignment, rejection, snapshot creation, and corrected approval while the Reviewer Work Queue remains read-only.

This is not production-ready because localhost has disposable data and direct operator control. A shared production or Railway-like demo environment does not. Non-local mutation can alter future demos, destroy repeatability, or create misleading audit history unless the environment, data, credentials, reset path, and host guards are isolated first.

## Required Staging Or Preview Environment

The first non-local mutation target must be one of:

- An isolated staging environment.
- An isolated preview environment.
- A separate Railway project or service set only if it has a separate database and no shared production demo patients.

It must not be:

- `https://access2.salvardata.com`
- `https://api.salvardata.com/api/v1`
- The shared production demo tenant.
- Any target that reuses production demo data or credentials.

Required isolation:

- Separate frontend URL from production.
- Separate backend API URL from production.
- Separate database from production.
- Separate synthetic tenant or organization for mutation validation.
- Separate admin/reviewer credentials from production demo credentials.
- Stable mutation-only patient markers that cannot overlap with `access2-railway-demo:*`.

## Synthetic Data Requirements

All staging mutation data must be synthetic-only.

The seed/reset path must create or repair a disposable scenario equivalent to the local proof:

- A synthetic patient marked for V2 mutation validation only.
- A latest `pending_review` immutable review packet snapshot.
- Persisted `packet_json` and `packet_markdown`.
- A completed intervention and measurable outcome baseline.
- Synthetic post-rejection corrected evidence, such as an improved `systolic_bp` outcome and care update.
- Historical rejected and approved snapshots preserved as read-only audit evidence.

No real PHI, secrets, production patient identifiers, or production demo patient markers may be used.

## Dedicated Seed And Reset Strategy

Staging needs its own seed/reset strategy before any mutation E2E runs there. Do not reuse the local-only seed directly against staging unless a separate implementation slice explicitly adapts and reviews it for staging.

Minimum seed/reset contract:

- Require explicit opt-in, separate from normal app startup.
- Refuse production and shared Railway-like targets by default.
- Print copy/paste-friendly patient IDs or environment-variable values for the E2E runner.
- Restore the disposable target to a latest `pending_review` snapshot before each run.
- Create a new latest snapshot after terminal states instead of rewriting rejected or approved packet content.
- Preserve all historical rejected and approved `packet_json` and `packet_markdown`.
- Keep mutation markers separate from all `access2-railway-demo:*` patients.
- Verify that shared production demo patients were not changed.

Rollback/reseed should mean restoring the staging disposable tenant to a known synthetic pre-test posture. It must not delete unrelated data or erase terminal audit history unless a future staging-only teardown design explicitly owns the whole disposable database.

## Mutation E2E Host Guards

Any staging mutation E2E must fail closed before login, seeding, or mutation if the configured frontend or API target looks unsafe.

The deny list must include at minimum:

- `access2.salvardata.com`
- `api.salvardata.com`
- `railway.app`
- `up.railway.app`

For a staging or preview target, use an allowlist in addition to the deny list. The allowlist should name the exact approved staging frontend and API hosts. A missing or unexpected host must stop the run.

The mutation E2E must remain separate from the production read-only E2E suite. Production E2E continues to validate read-only demo behavior and must not activate assignment, rejection, snapshot creation, corrected approval, or override approval mutation paths.

## Required Environment Variables

Use staging-specific names or values; do not commit actual secrets.

Required categories:

```text
ACCESS2_ENABLE_STAGING_MUTATION_E2E=true
ACCESS2_E2E_BASE_URL=<isolated staging frontend URL>
ACCESS2_E2E_API_BASE_URL=<isolated staging backend API URL>
ACCESS2_E2E_ADMIN_EMAIL=<staging-only admin email>
ACCESS2_E2E_ADMIN_PASSWORD=<staging-only admin password>
ACCESS2_STAGING_V2_MUTATION_PATIENT_ID=<seed output>
ACCESS2_STAGING_MUTATION_ALLOWED_HOSTS=<comma-separated exact staging hosts>
```

Do not use production demo credentials for staging mutation validation. Do not place passwords, tokens, database URLs, or API secrets in docs, code, screenshots, logs, pull requests, or committed `.env` files.

## Audit Evidence Expectations

A successful staging mutation proof should produce evidence that mirrors the localhost proof:

- `snapshot_assigned` audit evidence for the original pending packet.
- `snapshot_rejected` audit evidence with a non-empty reason.
- Rejected packet content preserved and unavailable for audit bundle export.
- Corrected synthetic outcome/evidence added after rejection.
- A new immutable pending snapshot created from current corrected evidence.
- Corrected packet approved through the normal approval path.
- `snapshot_approved` audit evidence for the corrected packet.
- Approved snapshot terminal/read-only and audit-bundle-ready.
- Historical rejected and approved snapshots visible and read-only.
- Reviewer Work Queue remains read-only and exposes no mutation controls.
- Audit bundle export and manifest verification continue to use persisted snapshot data.

The evidence must demonstrate the core ACCESS2 product principle: the intervention led to a measurable outcome, and the corrected outcome was captured in immutable audit evidence before approval.

## Production Must Remain Read-Only

Until a separate production promotion slice is approved, production remains:

- Synthetic/demo-only.
- Read-only for workflow mutation.
- Stable for stakeholder demos.
- Covered by production read-only E2E.
- Guarded by the existing expected mutation skips.

Do not mutate Demo Patient 3 or any `access2-railway-demo:*` patient for repeatable mutation validation. Demo Patient 3 remains the production read-only rejected-posture scenario.

## Promotion Path

Use this order:

1. Localhost proof: complete for assignment, rejection, corrected evidence, new snapshot creation, corrected approval, and terminal read-only posture.
2. Isolated staging or preview readiness: complete this document's environment, seed/reset, credentials, host-guard, and audit-evidence requirements.
3. Staging mutation implementation slice: add staging-specific seed/reset and E2E guard support without touching production demo data.
4. Staging validation: run mutation E2E only against the approved isolated target and record the audit evidence.
5. Production-safe feature-flag planning: decide whether patient-detail mutation controls can be enabled in production behind explicit governance and flags.
6. Production promotion: only after staging evidence, reset ownership, role governance, and rollback guidance are accepted.

Production mutation E2E is not part of this path until a future plan explicitly defines a production-safe disposable tenant or other controlled target.

## Why Override Approval Still Waits

Normal corrected approval proves that a packet can become audit-bundle-ready after measurable evidence is corrected and captured in a new immutable snapshot.

Superuser override approval is different. It can approve despite readiness gaps, so it needs separate governance:

- Who can override.
- Which missing evidence can be overridden.
- Required reason wording.
- Audit event language.
- Review visibility.
- Feature flagging.
- Separate tests and staging evidence.

Do not combine override approval with staging mutation readiness or corrected-packet approval promotion.

## Explicit Non-Goals

- No production demo mutation.
- No production mutation E2E.
- No broad workflow mutation controls.
- No override approval implementation.
- No Railway config changes in this slice.
- No backend startup command changes; it remains `bash scripts/render-start.sh`.
- No seed command as a Railway startup command.
- No real PHI.
- No secrets.
- No architecture redesign.

## Stop Conditions

Stop before any non-local mutation if:

- The target frontend or API host is production or Railway-like and not explicitly approved as isolated staging.
- The staging database is shared with production.
- The seed/reset command would touch `access2-railway-demo:*` patients.
- Staging credentials are missing, reused from production, or exposed in docs/logs.
- The E2E can run without explicit staging opt-in.
- Host guards rely only on convention instead of fail-closed code.
- Historical snapshot packet content would be rewritten.
- Reviewer Work Queue exposes mutation controls.
- The backend startup command or Railway configuration would need to change.
