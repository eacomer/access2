# ACCESS2 V2 Isolated Staging Environment Plan

## Purpose

This plan defines the isolated staging environment ACCESS2 V2 needs before any staging seed/reset implementation or staging mutation E2E is written or run.

Isolated staging is required before production-grade V2 promotion because the localhost correction-loop proof is complete, but localhost does not prove that non-local credentials, hosts, data isolation, reset ownership, and deployment operations are safe. The staging target must prove V2 mutation safety outside localhost without touching production, shared production demo data, or real PHI.

This plan is documentation only. It does not create staging, change Railway services, change Railway config, implement seed/reset, add staging mutation E2E, or authorize staging mutation execution.

## Environment Options

### Railway Preview Environment

Benefits:

- Close to the current production deployment model.
- Can be tied to branch or pull request workflows.
- Useful for short-lived validation when isolation is explicit.

Risks:

- Preview behavior can accidentally inherit production-like assumptions if environment variables, databases, or domains are copied without review.
- Operators may confuse preview URLs with production Railway URLs.
- Any Railway-like host still needs explicit allowlisting and must fail closed by default.

Operational complexity:

- Moderate. Preview setup can be convenient, but safe database, Redis, credential, and host separation must be verified every time.

Separate DB/data guarantee:

- Acceptable only if the preview target has its own Postgres, Redis, tenant, and synthetic seed/reset ownership.

Production coupling risk:

- Medium. The deployment shape is similar to production, so guardrails must explicitly prove the preview target is isolated.

### Separate Railway Staging Services Or Project

Benefits:

- Closest operational match to production while allowing explicit service, database, Redis, domain, and secret separation.
- Easier to document as a durable staging target than an ad hoc preview.
- Supports repeated dry-run, seed/reset, and future mutation validation with stable staging-only URLs.

Risks:

- Requires disciplined environment-variable and secret management.
- Still uses Railway-like infrastructure, so production and staging service names must be clearly separated.
- Mutation tooling must continue to block generic `railway.app` and `up.railway.app` targets unless a future implementation adds exact staging allowlists.

Operational complexity:

- Moderate to high. It requires a separate project or service set, separate data services, separate secrets, and documented ownership.

Separate DB/data guarantee:

- Strong if staging uses its own Postgres, Redis, synthetic tenant, credentials, and service/project boundaries.

Production coupling risk:

- Low to medium when implemented as a separate project or clearly separate service set. The main risk is copying production variables or using production demo data by mistake.

### Another Hosting Provider

Benefits:

- Can provide strong physical and operational separation from production Railway services.
- Reduces the chance of accidentally mutating Railway production services.

Risks:

- Adds deployment drift and provider-specific behavior not proven by the current production setup.
- May require new runbooks, health checks, secrets handling, and troubleshooting paths.
- Can distract from the V2 proof chain if the provider migration surface grows.

Operational complexity:

- High. This is more infrastructure work than the smallest staging prerequisite needs.

Separate DB/data guarantee:

- Potentially strong if provisioned carefully, but it requires new verification and operational ownership.

Production coupling risk:

- Low for Railway production coupling, but higher for architecture or deployment drift.

## Recommended Environment Strategy

The safest practical first choice is a separate Railway staging project or clearly separate Railway staging services, not the production services.

Recommended staging shape:

- Separate staging frontend service.
- Separate staging backend service.
- Separate staging Postgres.
- Separate staging Redis if Redis is used.
- Staging-specific frontend and backend URLs.
- Staging-only secrets and credentials.
- Synthetic-only seed data.
- No production custom domains.
- No shared production demo patients.
- No mutation of production Railway services.

This keeps staging close enough to production to validate deployment behavior while keeping data and operational boundaries explicit. Railway preview can be useful later, but a durable separate staging project or service set is easier to reason about for repeatable V2 mutation validation.

## Required Staging Boundaries

Staging must have:

- Separate frontend URL.
- Separate backend API URL.
- Separate database.
- Separate Redis if Redis is used.
- Separate JWT/session/auth secrets.
- Separate admin, reviewer, and demo credentials.
- Synthetic-only data.
- No imported production database dump.
- No production demo patient IDs.
- No `access2-railway-demo:*` mutation target.
- No production custom domains.
- No production Railway service mutation.

## Proposed Placeholder Names

Use placeholder values only:

```text
ACCESS2_STAGING_FRONTEND_URL=https://access2-v2-staging.example.test
ACCESS2_STAGING_API_BASE_URL=https://api-access2-v2-staging.example.test/api/v1
ACCESS2_STAGING_ENV_LABEL=v2-staging
ACCESS2_STAGING_DATA_CLASSIFICATION=synthetic
ACCESS2_STAGING_DATABASE_LABEL=access2-v2-staging-db
```

These are examples, not real infrastructure values. Do not commit real domains, credentials, tokens, database URLs, or secret-store values.

## Required Environment Variables

Use [access2-v2-staging-env-template.md](C:/dev/access2/docs/access2-v2-staging-env-template.md) as the source for placeholder staging variables.

Current dry-run guard variables:

```text
ACCESS2_STAGING_FRONTEND_URL
ACCESS2_STAGING_API_BASE_URL
ACCESS2_STAGING_ENV_LABEL
ACCESS2_STAGING_DATA_CLASSIFICATION
ACCESS2_STAGING_SEED_RESET_DRY_RUN
ACCESS2_ENABLE_STAGING_MUTATION_DRY_RUN
```

Future staging E2E will likely need a separate explicit staging mutation gate, for example:

```text
ACCESS2_ENABLE_STAGING_MUTATION_E2E
```

Do not introduce or use that gate until a future approved implementation slice adds and tests it. Staging admin, reviewer, and demo credentials must exist only in an approved secret store or local operator shell, never in docs, code, logs, screenshots, pull requests, or committed `.env` files.

## Dry-Run Guard Use

The current non-mutating dry-run guard command is:

```powershell
cd C:\dev\access2
py -3 backend\scripts\check_staging_v2_seed_reset_contract.py
```

The guard:

- Does not seed or reset data.
- Does not connect to a database.
- Does not make network calls.
- Does not authorize staging mutation E2E.
- Should pass only after safe staging placeholder or approved isolated staging values are set.
- Should fail safely when required dry-run variables are missing or unsafe.

## Host Guard And Production Refusal Requirements

Staging and mutation tooling must continue to refuse:

- `https://access2.salvardata.com`
- `https://api.salvardata.com/api/v1`
- `access2.salvardata.com`
- `api.salvardata.com`
- Railway production targets on `railway.app`
- Railway production targets on `up.railway.app`
- Missing URLs.
- Malformed URLs.
- Credential-bearing URLs.
- Query-string or token-bearing URLs.

Future staging mutation tooling must use exact staging host allowlists in addition to production deny rules. Missing or unexpected hosts must stop before login, seeding, reset, or mutation.

## Setup Sequence

This sequence defines the order of work only. Do not execute it as part of this planning slice.

1. Choose the staging environment strategy.
2. Provision isolated staging frontend and backend targets.
3. Provision separate staging Postgres and Redis.
4. Configure staging-only environment variables and secrets.
5. Confirm the backend startup command remains `bash scripts/render-start.sh` unless explicitly changed in a future approved slice.
6. Deploy staging from `main` or a controlled branch.
7. Verify live and ready health checks against staging only.
8. Run the dry-run seed/reset contract guard.
9. Only after approval, implement staging seed/reset.
10. Only after seed/reset exists, add a skipped/fail-closed staging mutation E2E skeleton.
11. Only after all gates pass, consider running staging mutation E2E.

## Validation Expectations

Before staging mutation E2E is ever allowed:

- Staging health checks pass.
- Staging database identity is confirmed not production.
- Staging data classification is `synthetic`.
- Dry-run guard passes.
- Staging mutation checklist is complete.
- Staging seed/reset implementation is reviewed.
- Mutation host guard blocks production-like hosts.
- Production read-only E2E remains separate and passing.
- Production demo data remains unchanged.

## Rollback And Cleanup Expectations

Staging must support cleanup without production impact:

- Staging can be reset to a known synthetic baseline.
- Staging secrets can be rotated independently.
- Staging data can be dropped without affecting production.
- Generated Playwright artifacts are not committed.
- Failed staging setup has a documented cleanup path.
- Partial seed/reset or mutation attempts can be diagnosed without exposing credentials or rewriting immutable historical packets unexpectedly.

## Open Questions

- Should staging use Railway preview or a separate Railway project/services?
- What exact staging domain names will be used?
- What database identity signal can the dry-run guard safely verify later?
- What future staging mutation gate variable should be used?
- Who owns staging credentials?
- Should staging seed/reset clean disposable scenarios or version them?
- Should staging deploy from `main` or a staging branch?

## Non-Goals

- No staging implementation in this slice.
- No staging seed/reset implementation.
- No staging mutation E2E.
- No production mutation E2E.
- No production demo data mutation.
- No superuser override approval.
- No broad workflow mutation controls.
- No Railway config changes.
- No backend behavior changes.
- No frontend behavior changes.
- No E2E behavior changes.
- No real PHI.
- No secrets.

## Recommended Next Step

If the user is ready to create staging infrastructure, the next slice should create a concrete staging provisioning checklist.

If staging infrastructure is not ready, return to non-staging ACCESS2 V2 product workflow improvements that strengthen the audit proof chain without expanding mutation scope.
