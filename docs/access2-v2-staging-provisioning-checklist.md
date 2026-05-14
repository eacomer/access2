# ACCESS2 V2 Staging Provisioning Checklist

## Purpose And Use

Use this checklist before creating or validating any ACCESS2 V2 staging environment.

This checklist is operational, but it is still documentation only. It is not permission to run staging mutation E2E, and it does not replace:

- [access2-v2-staging-mutation-checklist.md](C:/dev/access2/docs/access2-v2-staging-mutation-checklist.md)
- [access2-v2-staging-env-template.md](C:/dev/access2/docs/access2-v2-staging-env-template.md)
- [access2-v2-staging-seed-reset-contract.md](C:/dev/access2/docs/access2-v2-staging-seed-reset-contract.md)
- `backend/scripts/check_staging_v2_seed_reset_contract.py`

## 1. Pre-Provisioning Decision

- [ ] Choose one staging strategy:
  - [ ] Separate Railway project/services.
  - [ ] Railway preview environment.
  - [ ] Another host.
- [ ] Record selected strategy: `<selected-staging-strategy>`.
- [ ] Record rationale: `<short-rationale>`.
- [ ] Confirm no production Railway service will be modified.
- [ ] Confirm production custom domains are not reused.
- [ ] Confirm the target is synthetic-only and contains no real PHI.

## 2. Service Isolation Checklist

- [ ] Create or identify staging frontend service.
- [ ] Create or identify staging backend service.
- [ ] Confirm staging frontend URL placeholder:

```text
https://access2-v2-staging.example.test
```

- [ ] Confirm staging backend API URL placeholder:

```text
https://api-access2-v2-staging.example.test/api/v1
```

- [ ] Confirm staging frontend URL is not:

```text
https://access2.salvardata.com
```

- [ ] Confirm staging backend API URL is not:

```text
https://api.salvardata.com/api/v1
```

- [ ] Confirm staging hostnames are not production Railway hosts.
- [ ] Confirm staging services can be deleted or reset without affecting production.
- [ ] Confirm staging frontend and backend service names are visibly distinct from production service names.

## 3. Data Service Isolation

- [ ] Create separate staging Postgres.
- [ ] Create separate staging Redis if Redis is required.
- [ ] Confirm staging DB is not the production DB.
- [ ] Confirm no production DB dump or import is used.
- [ ] Confirm staging data classification is:

```text
synthetic
```

- [ ] Record non-secret DB label:

```text
access2-v2-staging-db
```

- [ ] Record non-secret Redis label if used: `<access2-v2-staging-redis-label>`.
- [ ] Confirm staging data can be dropped or reset without production impact.
- [ ] Confirm staging data will not reuse `access2-railway-demo:*` mutation targets.

## 4. Environment Variables And Secrets

- [ ] Configure staging-only environment variables.
- [ ] Use [access2-v2-staging-env-template.md](C:/dev/access2/docs/access2-v2-staging-env-template.md).
- [ ] Confirm no secrets are committed.
- [ ] Confirm staging credentials differ from production credentials.
- [ ] Confirm JWT/session/auth secrets differ from production.
- [ ] Confirm staging admin credentials are stored only in an approved secret store.
- [ ] Confirm staging reviewer credentials are stored only in an approved secret store.
- [ ] Confirm staging demo credentials are stored only in an approved secret store.
- [ ] Confirm `FRONTEND_ORIGIN` or CORS values point only to the staging frontend where relevant.
- [ ] Confirm backend API base URL values point only to the staging backend where relevant.
- [ ] Confirm backend startup command remains:

```text
bash scripts/render-start.sh
```

- [ ] Confirm any backend startup command change is deferred to a future approved slice.

## 5. Deployment Setup Checklist

- [ ] Deploy backend staging from `main` or a controlled branch.
- [ ] Deploy frontend staging from `main` or a controlled branch.
- [ ] Confirm no seed commands are configured as startup commands.
- [ ] Confirm no staging mutation flags are enabled by default.
- [ ] Confirm generated build artifacts are not committed.
- [ ] Confirm production deployment remains untouched.
- [ ] Confirm staging deploy logs do not expose tokens, passwords, or database URLs.

## 6. Health And Smoke Validation

- [ ] Verify staging backend live health endpoint.
- [ ] Verify staging backend ready health endpoint.
- [ ] Verify staging frontend loads.
- [ ] Verify staging login uses staging backend only.
- [ ] Verify cookies and session behavior are scoped to the staging domain.
- [ ] Verify no production frontend URLs appear in staging browser or network traces.
- [ ] Verify no production backend URLs appear in staging browser or network traces.
- [ ] Do not run mutation E2E at this stage.

## 7. Dry-Run Guard Validation

- [ ] Set only non-secret staging dry-run variables.
- [ ] Run:

```powershell
cd C:\dev\access2
py -3 backend\scripts\check_staging_v2_seed_reset_contract.py
```

- [ ] Confirm dry-run passes only for staging values.
- [ ] Confirm dry-run fails for production-like values.
- [ ] Record sanitized dry-run result only.
- [ ] Confirm dry-run output does not include passwords, tokens, database URLs, query strings, URL usernames, or URL passwords.
- [ ] Confirm the operator understands that dry-run does not seed, reset, connect to DB, or authorize staging mutation E2E.

## 8. Production Protection Checklist

- [ ] Production read-only E2E remains separate.
- [ ] Production demo data is untouched.
- [ ] Production Railway config is untouched.
- [ ] Production backend startup command is unchanged.
- [ ] Production custom domains are untouched.
- [ ] Mutation host guard still blocks production/custom-domain and Railway-like hosts.
- [ ] `https://access2.salvardata.com` is not used as a mutation target.
- [ ] `https://api.salvardata.com/api/v1` is not used as a mutation target.
- [ ] `railway.app` and `up.railway.app` production targets are not used as mutation targets.

## 9. Go/No-Go Checkpoint

- [ ] Go only if all isolation, secret, health, and dry-run checks pass.
- [ ] No-go if any URL, DB, secret, or data classification is uncertain.
- [ ] No-go if staging could touch production data.
- [ ] No-go if production-like hostnames appear anywhere in mutation target variables.
- [ ] No-go if real PHI is present.
- [ ] No-go if rollback or reset path is unclear.
- [ ] No-go if production Railway config would need to change.
- [ ] No-go if backend startup behavior would need to change without a future approved slice.

## 10. Handoff Before Next Implementation

- [ ] Record selected staging strategy.
- [ ] Record sanitized frontend staging URL.
- [ ] Record sanitized backend staging API URL.
- [ ] Record non-secret DB label.
- [ ] Record non-secret Redis label if used.
- [ ] Record dry-run guard result.
- [ ] Record health check result.
- [ ] Record known open risks.
- [ ] Confirm the next implementation candidate is staging seed/reset implementation only after staging is provisioned and verified.

## Explicit Non-Goals

- [ ] No staging provisioning performed by this doc.
- [ ] No Railway config changes in this slice.
- [ ] No staging seed/reset implementation.
- [ ] No staging mutation E2E.
- [ ] No production mutation E2E.
- [ ] No production demo data mutation.
- [ ] No superuser override approval.
- [ ] No broad workflow mutation controls.
- [ ] No backend behavior changes.
- [ ] No frontend behavior changes.
- [ ] No E2E behavior changes.
- [ ] No real PHI.
- [ ] No secrets.
