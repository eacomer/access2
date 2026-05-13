# ACCESS2 V2 Staging Mutation Safety Checklist

## Purpose

Use this checklist as the final operator gate before any ACCESS2 V2 mutation E2E is run outside localhost.

This is an operational checklist only. It does not authorize production mutation testing, shared production demo-data mutation, Railway configuration changes, backend startup command changes, override approval implementation, or broad workflow mutation controls.

## When To Use This Checklist

Use this checklist when all of these are true:

- [ ] The localhost-only V2 correction-loop proof is already complete.
- [ ] An isolated staging or preview target has been provisioned for synthetic mutation validation.
- [ ] The operator is preparing to run staging mutation seed/reset or mutation E2E for the first time, or after any staging environment change.
- [ ] The operator can stop before execution if any item below is unclear or fails.

## When Not To Use This Checklist

Do not use this checklist to justify mutation testing when any of these are true:

- [ ] The target is `https://access2.salvardata.com`.
- [ ] The target API is `https://api.salvardata.com/api/v1`.
- [ ] The target uses production or shared demo data.
- [ ] The target contains real PHI.
- [ ] The operator is trying to run production mutation E2E.
- [ ] The operator is trying to add superuser override approval or broad workflow controls.

## 1. Target Environment Confirmation

- [ ] Target frontend URL is not `https://access2.salvardata.com`.
- [ ] Target backend API URL is not `https://api.salvardata.com/api/v1`.
- [ ] Target host is not Railway production.
- [ ] Target host is not a production custom domain.
- [ ] Target frontend URL is an approved isolated staging or preview URL.
- [ ] Target backend API URL is an approved isolated staging or preview API URL.
- [ ] Operator records exact frontend URL before running mutation tests: `<frontend-url>`.
- [ ] Operator records exact backend API URL before running mutation tests: `<backend-api-url>`.

## 2. Database And Data Isolation

- [ ] Staging database is separate from production database.
- [ ] Staging database is not shared with the production demo tenant.
- [ ] Staging database contains synthetic-only data.
- [ ] No real PHI is present.
- [ ] Mutation-only patients use markers that cannot overlap with `access2-railway-demo:*`.
- [ ] Seed/reset command has been reviewed before execution.
- [ ] Reset strategy is documented.
- [ ] Reset strategy has been tested against the isolated staging or preview target.

## 3. Credentials And Secrets

- [ ] Staging admin credentials are separate from production credentials.
- [ ] Staging reviewer credentials are separate from production credentials.
- [ ] No secrets are committed to the repo.
- [ ] No secrets are written into docs.
- [ ] Environment variables are set only in the local shell or an approved secret store.
- [ ] Screenshots do not expose passwords, tokens, database URLs, or API secrets.
- [ ] Logs do not expose passwords, tokens, database URLs, or API secrets.
- [ ] Pull requests do not include credentials, tokens, or secret values.

## 4. Mutation Gate And Host Guards

- [ ] `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` or a future staging-specific mutation gate is explicitly enabled only for the safe target.
- [ ] The mutation E2E fails closed when the frontend URL is missing.
- [ ] The mutation E2E fails closed when the backend API URL is missing.
- [ ] Fail-closed checks block `access2.salvardata.com`.
- [ ] Fail-closed checks block `api.salvardata.com`.
- [ ] Fail-closed checks block `railway.app`.
- [ ] Fail-closed checks block `up.railway.app`.
- [ ] Test refuses to run if the target URL is production-like.
- [ ] Operator confirms the resolved frontend and backend API targets before execution.

## 5. Seed/Reset Readiness

- [ ] Staging seed/reset creates a disposable corrected-packet scenario.
- [ ] Seed/reset starts from a latest `pending_review` review packet snapshot.
- [ ] Seed/reset creates or preserves a completed intervention and measurable outcome baseline.
- [ ] Seed/reset can create corrected synthetic evidence after rejection.
- [ ] Reruns are idempotent or clearly reset state to a known synthetic baseline.
- [ ] Terminal historical snapshots are not rewritten.
- [ ] Rejected terminal snapshots are not rewritten.
- [ ] Approved terminal snapshots are not rewritten.
- [ ] Old `packet_json` remains immutable.
- [ ] Old `packet_markdown` remains immutable.

## 6. E2E Execution Readiness

- [ ] Mutation E2E is separate from production read-only E2E.
- [ ] Production read-only E2E remains unchanged.
- [ ] Operator confirms the exact command before execution.
- [ ] Operator confirms all required environment variables before execution.
- [ ] Expected mutation flow is assignment -> rejection -> new corrected snapshot -> approval.
- [ ] Expected terminal posture is approved and read-only.
- [ ] Expected result is recorded with date.
- [ ] Expected result is recorded with target frontend/backend URLs.
- [ ] Expected result is recorded as pass/fail.
- [ ] Any failure is recorded before rerun or cleanup.

## 7. Rollback/Reseed

- [ ] Rollback or reseed command is available before mutation E2E starts.
- [ ] Failed mutation run has a documented cleanup path.
- [ ] Staging can be returned to a known synthetic baseline.
- [ ] Reseed does not delete unrelated staging data.
- [ ] Reseed does not erase terminal audit history unless the entire target is explicitly disposable.
- [ ] Post-run verification confirms the disposable scenario is ready for the next run or intentionally parked.

## 8. Production Protections

- [ ] Production E2E remains read-only.
- [ ] Reviewer Work Queue remains read-only.
- [ ] No production demo mutation is run.
- [ ] No production seed/reset mutation is run.
- [ ] No broad workflow mutation controls are introduced.
- [ ] No superuser override approval is introduced.
- [ ] Demo Patient 3 remains the production read-only rejected-posture scenario.
- [ ] `access2-railway-demo:*` patients remain stable for production demos.
- [ ] Railway config is unchanged.
- [ ] Backend startup command remains `bash scripts/render-start.sh`.

## 9. Evidence/Audit Expectations

- [ ] Rejected snapshot remains historical evidence.
- [ ] Rejected snapshot keeps persisted `packet_json`.
- [ ] Rejected snapshot keeps persisted `packet_markdown`.
- [ ] Corrected snapshot is created from current corrected evidence.
- [ ] Approved corrected snapshot is terminal/read-only.
- [ ] Audit bundle expectations are documented before promotion.
- [ ] Manifest verification expectations are documented before promotion.
- [ ] Operator records validation artifacts without committing generated reports.
- [ ] Operator records snapshot IDs and relevant audit-event observations outside committed secrets/logs.

## 10. Go/No-Go Decision

- [ ] All checklist items above pass before staging mutation E2E.
- [ ] Any uncertainty means stop and do not run mutation tests.
- [ ] Any production-like target means stop and do not run mutation tests.
- [ ] Any missing reset path means stop and do not run mutation tests.
- [ ] Any credential or secret-handling uncertainty means stop and do not run mutation tests.
- [ ] Production mutation remains prohibited until explicitly planned in a future approved slice.

## Stop Conditions

Stop immediately and do not run mutation seed/reset or mutation E2E if:

- [ ] The target frontend URL is `https://access2.salvardata.com`.
- [ ] The target backend API URL is `https://api.salvardata.com/api/v1`.
- [ ] The target appears to be Railway production or a production custom domain.
- [ ] The staging database is not proven separate from production.
- [ ] Any real PHI may be present.
- [ ] Any secret would be committed, logged, screenshotted, or pasted into docs.
- [ ] Host guards are missing or do not fail closed.
- [ ] Reset/reseed is not documented and tested.
- [ ] Historical `packet_json` or `packet_markdown` would be rewritten.
- [ ] Reviewer Work Queue exposes mutation controls.
- [ ] Backend startup command or Railway configuration would need to change.
