# ACCESS2 V2 Mutation E2E Guard Behavior

## Purpose

This document explains how ACCESS2 V2 mutation E2E target guards are expected to behave for current localhost mutation validation and future isolated staging work.

It is an operator and implementation safety note only. It does not authorize staging mutation E2E, production mutation E2E, production demo-data mutation, Railway configuration changes, backend startup command changes, or new workflow controls.

## Current Localhost Mutation Behavior

Local mutation E2E is currently the only approved mutation E2E path.

The approved local command remains:

```powershell
cd C:\dev\access2\frontend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:ACCESS2_E2E_BASE_URL="http://localhost:3001"
$env:ACCESS2_E2E_API_BASE_URL="http://localhost:8000/api/v1"
$env:ACCESS2_E2E_ADMIN_EMAIL="admin@example.com"
$env:ACCESS2_E2E_ADMIN_PASSWORD="Admin123!"
$env:ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID="<value printed by local seed script>"
& "C:\Program Files\nodejs\npm.cmd" run test:e2e:local-mutation
```

Current local mutation requirements:

- `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` must be set.
- `ACCESS2_E2E_BASE_URL` must point to a safe localhost or loopback frontend target.
- `ACCESS2_E2E_API_BASE_URL` must point to a safe localhost or loopback backend API target.
- `ACCESS2_E2E_ADMIN_EMAIL` and `ACCESS2_E2E_ADMIN_PASSWORD` must be set in the current shell only.
- `ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID` should identify the disposable local mutation patient when available.
- The local seed marker remains `access2-local-v2-mutation:reviewer-rejection`.

Latest known localhost result:

```text
npm run test:e2e:local-mutation
1 passed in about 2.6 minutes
```

If required local mutation env vars are missing, do not run mutation E2E. Skipping is the safe behavior.

## Shared Host Guard Helper

Mutation target refusal is centralized in:

```text
frontend/e2e/helpers/mutation-host-guard.ts
```

The local mutation spec calls this helper before mutation steps. The guard evaluates the configured frontend and backend API targets before login and before any review-packet mutation action.

Default allowed targets:

- `localhost`
- `127.0.0.1`
- `[::1]` or `::1` when URL parsing reports IPv6 loopback safely

Default blocked targets:

- Missing target URL.
- Malformed target URL.
- Any non-local target without an explicit allowlist.
- Any production-like target.

## Production And Railway-Like Host Behavior

Mutation E2E must always block these exact production/custom-domain targets:

- `https://access2.salvardata.com`
- `https://api.salvardata.com/api/v1`

Mutation E2E must also block target hostnames containing these markers:

- `access2.salvardata.com`
- `api.salvardata.com`
- `railway.app`
- `up.railway.app`

This applies to both frontend and backend API targets. A mixed pair is unsafe if either side is production-like, for example:

- frontend localhost with production API
- production frontend with backend localhost
- any Railway-like frontend or API target

Unknown non-local targets must block unless a future staging implementation passes an explicit allowlist after the staging environment, database, credentials, seed/reset, and operator checklist are complete.

## Error Message Safety

Guard errors must say mutation E2E is blocked and include only sanitized target labels or hostnames.

Guard errors must not expose:

- Passwords.
- Tokens.
- Query strings.
- URL usernames.
- URL passwords.
- Database URLs.
- Secret values.

Credential-bearing or query-bearing URLs should still block by host, but diagnostics should not echo sensitive URL parts.

## Future Staging Mutation Behavior

Staging mutation E2E is not implemented yet.

Before any future staging mutation E2E exists, the staging target must satisfy:

- [access2-v2-staging-mutation-readiness.md](C:/dev/access2/docs/access2-v2-staging-mutation-readiness.md)
- [access2-v2-staging-mutation-checklist.md](C:/dev/access2/docs/access2-v2-staging-mutation-checklist.md)
- [access2-v2-staging-env-template.md](C:/dev/access2/docs/access2-v2-staging-env-template.md)
- [access2-v2-staging-seed-reset-contract.md](C:/dev/access2/docs/access2-v2-staging-seed-reset-contract.md)

Future staging behavior must require:

- An explicit staging-safe gate or equivalent opt-in.
- Exact staging frontend and backend API target URLs recorded before execution.
- An isolated staging database that is not production.
- Synthetic-only staging data.
- A staging seed/reset process satisfying the seed/reset contract.
- Explicit allowed staging hostnames passed to the mutation host guard.

The current helper can allow future non-local staging hosts only when a caller passes an explicit allowlist. That support is not permission to run staging mutation E2E today.

## Safe Failure Behavior

Failing closed is the intended safety behavior.

Guard refusal is successful protection when:

- The frontend URL is production-like.
- The backend API URL is production-like.
- Either target is missing.
- Either target is malformed.
- Either target is unknown and non-local.
- A URL includes credentials or query strings but resolves to a blocked host.

Guard failure should happen before any mutation step. Production read-only E2E remains separate and must not use mutation paths.

## Operator Checklist

Before any localhost mutation E2E run:

- Confirm the frontend URL is localhost or loopback.
- Confirm the backend API URL is localhost or loopback.
- Confirm local backend and frontend are already running.
- Confirm `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` is set only in the current shell.
- Confirm the disposable local seed/reset was run only against a safe local target.
- Confirm credentials are set only in the current shell and are not committed.
- Confirm generated Playwright artifacts are not committed.

Before any future staging mutation E2E run:

- Confirm staging mutation E2E has actually been implemented and approved.
- Confirm frontend and backend API target URLs are recorded.
- Confirm the database is not production.
- Confirm data is synthetic-only.
- Confirm the seed/reset contract is satisfied.
- Confirm the exact staging host allowlist is configured.
- Stop if any target, credential, database, or reset path is unclear.

## Non-Goals

- No staging mutation E2E in this slice.
- No production mutation E2E.
- No production demo-data mutation.
- No Railway config changes.
- No backend behavior changes.
- No product frontend behavior changes.
- No real PHI.
- No secrets.
