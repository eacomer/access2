# ACCESS2 V2 Staging Environment Template

## Purpose

This is a preparation document only.

It documents placeholder environment variables and command shapes for a future isolated staging or preview ACCESS2 V2 mutation test run. It must not be used against production, shared production demo data, Railway production targets, or any environment containing real PHI.

This document does not authorize staging mutation E2E execution. Before any non-local mutation run, the isolated target must satisfy [access2-v2-staging-mutation-readiness.md](C:/dev/access2/docs/access2-v2-staging-mutation-readiness.md) and [access2-v2-staging-mutation-checklist.md](C:/dev/access2/docs/access2-v2-staging-mutation-checklist.md).

## Non-Secret Placeholders Only

Use placeholders in docs and examples:

```text
<STAGING_FRONTEND_URL>
<STAGING_BACKEND_API_URL>
<STAGING_ADMIN_EMAIL>
<STAGING_ADMIN_PASSWORD>
<STAGING_DEMO_PATIENT_ID>
<STAGING_ALLOWED_HOSTS>
```

Do not add real credentials, tokens, database URLs, patient identifiers from production, or secret values to this file.

## Current E2E Variable Names

The current local V2 mutation E2E reads these variables:

```text
ACCESS2_ENABLE_LOCAL_MUTATION_E2E
ACCESS2_E2E_BASE_URL
ACCESS2_E2E_API_BASE_URL
ACCESS2_E2E_ADMIN_EMAIL
ACCESS2_E2E_ADMIN_PASSWORD
ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID
```

Current helper behavior:

- `ACCESS2_E2E_BASE_URL` is the frontend target.
- `ACCESS2_E2E_API_BASE_URL` is the backend API override used by `frontend/e2e/helpers/access2.ts`.
- If `ACCESS2_E2E_API_BASE_URL` is missing, the helper derives a local API URL from `ACCESS2_E2E_BASE_URL`.
- `ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID` narrows the local mutation spec to the seeded disposable patient when provided.
- The current code does not use `ACCESS2_API_BASE_URL` for this Playwright helper path.

## Required Variables For Future Staging Mutation Testing

A future staging mutation E2E should use staging-specific values equivalent to:

```powershell
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true" # current gate name; replace with a reviewed staging-specific gate when implemented
$env:ACCESS2_E2E_BASE_URL="<STAGING_FRONTEND_URL>"
$env:ACCESS2_E2E_API_BASE_URL="<STAGING_BACKEND_API_URL>"
$env:ACCESS2_E2E_ADMIN_EMAIL="<STAGING_ADMIN_EMAIL>"
$env:ACCESS2_E2E_ADMIN_PASSWORD="<STAGING_ADMIN_PASSWORD>"
$env:ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID="<STAGING_DEMO_PATIENT_ID>"
```

If a future implementation adds a staging-specific gate, prefer a clearer name such as:

```text
ACCESS2_ENABLE_STAGING_MUTATION_E2E
```

Do not invent or use that staging gate until a code slice actually implements and tests it.

## Current Localhost Command Shape

This command shape is localhost-only and is included for reference:

```powershell
cd C:\dev\access2\frontend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:ACCESS2_E2E_BASE_URL="http://localhost:3001"
$env:ACCESS2_E2E_API_BASE_URL="http://localhost:8000/api/v1"
$env:ACCESS2_E2E_ADMIN_EMAIL="admin@example.com"
$env:ACCESS2_E2E_ADMIN_PASSWORD="Admin123!"
$env:ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID="<value printed by local seed script>"
npm run test:e2e:local-mutation
```

Latest known local-only result:

```text
npm run test:e2e:local-mutation
1 passed in about 2.6 minutes on localhost only
```

Do not reuse the local command against production or shared demo data.

## Future Staging Command Shape

This is a placeholder command shape only. It is not currently approved to run.

Do not run it until all of these are complete:

- Isolated staging or preview frontend and API targets exist.
- Staging database is separate from production.
- Staging seed/reset path exists and has been reviewed.
- Host guards fail closed for production-like targets.
- [access2-v2-staging-mutation-checklist.md](C:/dev/access2/docs/access2-v2-staging-mutation-checklist.md) is complete.

Placeholder:

```powershell
cd C:\dev\access2\frontend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:ACCESS2_E2E_BASE_URL="<STAGING_FRONTEND_URL>"
$env:ACCESS2_E2E_API_BASE_URL="<STAGING_BACKEND_API_URL>"
$env:ACCESS2_E2E_ADMIN_EMAIL="<STAGING_ADMIN_EMAIL>"
$env:ACCESS2_E2E_ADMIN_PASSWORD="<STAGING_ADMIN_PASSWORD>"
$env:ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID="<STAGING_DEMO_PATIENT_ID>"
npm run test:e2e:local-mutation
```

Forbidden targets:

- `https://access2.salvardata.com`
- `https://api.salvardata.com/api/v1`
- `railway.app` production targets
- `up.railway.app` production targets
- any production custom domain
- any environment with real PHI

## Host Guard Expectations

A future staging command must fail closed before login, seed/reset, or mutation if the target is missing or production-like.

Required deny markers:

```text
access2.salvardata.com
api.salvardata.com
railway.app
up.railway.app
```

Operator requirements:

- Record the exact frontend URL before running.
- Record the exact backend API URL before running.
- Confirm neither URL is production or production-like.
- Confirm the target is an approved isolated staging or preview environment.
- Stop if the URL is missing, ambiguous, or copied from production.

## Seed/Reset Placeholders

Staging requires a separate seed/reset command later.

Do not invent or run a staging seed command in this docs slice. The existing local seed script, `backend/scripts/seed_local_v2_rejection_mutation.py`, is localhost-oriented and guarded by `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true`. It must not be run against production, Railway production, shared demo data, or any staging target unless a future implementation explicitly adapts and reviews it for that isolated target.

Current dry-run-only contract check:

```powershell
cd C:\dev\access2
$env:ACCESS2_STAGING_SEED_RESET_DRY_RUN="true"
$env:ACCESS2_ENABLE_STAGING_MUTATION_DRY_RUN="true"
$env:ACCESS2_STAGING_FRONTEND_URL="https://access2-v2-preview.example.test"
$env:ACCESS2_STAGING_API_BASE_URL="https://api-access2-v2-preview.example.test/api/v1"
$env:ACCESS2_STAGING_ENV_LABEL="v2-preview"
$env:ACCESS2_STAGING_DATA_CLASSIFICATION="synthetic"
py -3 backend\scripts\check_staging_v2_seed_reset_contract.py
```

This command validates only non-secret inputs for a future staging seed/reset. It performs no database connection, no network call, no seed, no reset, and no mutation E2E run.

Expected missing-variable refusal:

```powershell
cd C:\dev\access2
py -3 backend\scripts\check_staging_v2_seed_reset_contract.py
```

This should fail safely until the explicit dry-run and staging mutation dry-run gates are set. A passing run prints only sanitized target summaries; refusal output must not expose passwords, tokens, database URLs, query strings, URL usernames, or URL passwords.

The dry-run check must fail for production custom domains, `railway.app` or `up.railway.app` hosts, non-synthetic data classification, production-like environment labels, credential-bearing URLs, query strings, and missing gates. It is not permission to run staging mutation E2E.

Future staging seed/reset should provide placeholder output shaped like:

```text
ACCESS2_STAGING_V2_MUTATION_PATIENT_ID=<STAGING_DEMO_PATIENT_ID>
```

It must create or repair a disposable corrected-packet scenario without rewriting terminal historical snapshots or mutating `access2-railway-demo:*` patients.

## Secret Handling

- Keep real values in the current shell session or an approved secret store only.
- Do not commit `.env` files.
- Do not paste secrets into docs.
- Do not paste secrets into logs.
- Do not include secrets in screenshots.
- Redact tokens and passwords from diagnostics.
- Do not use production credentials for staging mutation validation.

## Promotion Readiness

This template is not permission to run staging mutation E2E.

Before any staging mutation run:

- Complete [access2-v2-staging-mutation-readiness.md](C:/dev/access2/docs/access2-v2-staging-mutation-readiness.md).
- Complete [access2-v2-staging-mutation-checklist.md](C:/dev/access2/docs/access2-v2-staging-mutation-checklist.md).
- Confirm seed/reset ownership.
- Confirm host guards fail closed.
- Confirm staging credentials and data are synthetic-only.

Production remains read-only until a future approved production promotion plan exists.

## Explicit Non-Goals

- No staging execution in this slice.
- No production mutation E2E.
- No production data mutation.
- No override approval.
- No Railway config changes.
- No backend behavior changes.
- No frontend behavior changes.
- No E2E code changes.
- No real PHI.
- No secrets.
