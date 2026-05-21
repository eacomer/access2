# ACCESS2 V2 Demo Readiness Handoff

## Purpose

This handoff explains the current ACCESS2 V2 demo-ready state after the completed localhost correction-loop proof and product clarity polish.

It is not a production mutation handoff. It is not a staging implementation handoff. It consolidates what an operator can safely show today and what must remain out of scope until staging or production guardrails change through a separate approved slice.

For stakeholder-facing review of the complete ACCESS2 demo package, start with [access2-stakeholder-demo-package-index.md](C:/dev/access2/docs/access2-stakeholder-demo-package-index.md). For V2-only local correction-loop operator handoff, start with [access2-v2-local-demo-handoff-index.md](C:/dev/access2/docs/access2-v2-local-demo-handoff-index.md).

## Current Demo Posture

- V1 production demo remains read-only and synthetic/demo-only.
- V2 mutation and correction-loop behavior is localhost-only.
- Outcome Evidence Readiness is a read-only display layer on patient detail when persisted packet evidence is available.
- The staging path is documented, but staging is not implemented.
- Production mutation remains prohibited.
- Shared production demo data must not be mutated.

## V2 Proof Story

The local V2 proof shows this controlled correction-loop story:

1. A reviewer assigns the latest `pending_review` review packet snapshot.
2. The reviewer rejects the original packet with a non-empty reason.
3. The rejected packet remains immutable historical evidence.
4. Historical `packet_json` and `packet_markdown` are not refreshed or overwritten.
5. Corrected evidence posture creates a new review packet snapshot.
6. Outcome Evidence Readiness can show the synthetic ACCESS track, metric, baseline, follow-up, readiness status, evidence completeness, and care update milestone from the persisted packet.
7. The corrected latest `pending_review` packet is approved.
8. The approved packet becomes terminal and read-only.
9. Historical approved and rejected snapshots remain read-only.
10. Audit bundle exports package the persisted snapshot evidence.
11. Manifest verification confirms the exported artifacts match persisted evidence.

## Operator Clarity Checkpoint - May 19, 2026

Use this checkpoint before a live localhost-only V2 walkthrough so the presenter explains the correction loop consistently:

- The latest actionable packet is the newest review packet snapshot with `review_status=pending_review`; assignment, rejection, and approval controls must apply only to that current pending packet.
- A rejected terminal snapshot remains preserved and read-only because it is the audit record of what was reviewed, who made the decision, when it happened, and why it was rejected.
- Corrected/new snapshot creation proves the correction loop by capturing the current corrected evidence in a new immutable packet instead of editing, refreshing, or repairing the rejected packet.
- Approval must apply only to the corrected latest pending snapshot, after the persisted review checklist has no missing evidence, so the approved packet represents the corrected current case state.
- Outcome Evidence Readiness should be explained as read-only evidence readiness, not a CMS submission, claims submission, billing workflow, or mutation control. The presenter should identify the ACCESS track/condition, metric, baseline/follow-up, outcome readiness status, completeness, and care update milestone when shown.
- `audit_bundle.available=true` is the handoff point from review workflow to audit-package posture; it means the corrected approved snapshot is ready for bundle export and later manifest verification.
- All assignment, rejection, corrected/new snapshot creation, and approval mutation remains localhost-only. Do not run these steps against production, Railway, staging, `https://`, or non-loopback targets.

## ACCESS2 Proof Chain Talk Track

Use this chain when explaining why the correction loop matters:

```text
signal -> escalation -> intervention -> outcome -> care update -> evidence -> case summary -> immutable review packet snapshot -> assignment -> review decision -> audit bundle -> manifest verification
```

Concise demo phrase:

```text
The snapshot captures the evidence. The bundle exports it. The manifest verifies what was exported.
```

Outcome evidence phrase:

```text
This is not a claim submission or CMS submission. This is the evidence-readiness layer that helps a provider prove whether the outcome story is complete enough for review.
```

## Demo Prerequisites

- Local backend is running.
- Local frontend is running.
- `frontend/.env.local` points to the local backend API:

  ```text
  http://localhost:8000/api/v1
  ```

- The local seed/reset script has been run:

  ```text
  backend/scripts/seed_local_v2_rejection_mutation.py
  ```

- Safe localhost mutation environment variables are set.
- `ACCESS2_E2E_API_BASE_URL` is set to the local backend API when running local mutation E2E:

  ```text
  http://localhost:8000/api/v1
  ```

- No real PHI is used.
- No production URLs are present in local mutation target variables.
- No Railway production targets are present in local mutation target variables.

## Required Local-Only Variables And Markers

Use these exact local V2 marker and variable names:

- Disposable local marker: `access2-local-v2-mutation:reviewer-rejection`
- Local mutation gate: `ACCESS2_ENABLE_LOCAL_MUTATION_E2E`
- Local frontend target: `ACCESS2_E2E_BASE_URL`
- Local backend API target: `ACCESS2_E2E_API_BASE_URL`
- Local admin email variable: `ACCESS2_E2E_ADMIN_EMAIL`
- Local admin password variable: `ACCESS2_E2E_ADMIN_PASSWORD`
- Seeded local patient ID variable: `ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID`

Do not commit local `.env` files or paste credentials into screenshots, logs, tickets, or handoff notes.

## Validation Summary

Latest known validation from the completed V2 correction-loop and product clarity sequence:

- Local rehearsal on May 16, 2026 passed on localhost only: `npm run test:e2e:local-mutation` completed with `1 passed (10.6m)` using frontend `http://localhost:3000` and API `http://localhost:8000/api/v1`.
- The rehearsal used the disposable local patient `3a3dbb11-f8f5-4ac3-8f3a-4dcd8b48160d`; seed/reset was needed because the marker was absent and again after partial local timeout attempts.
- The rehearsal verified assignment persistence, rejection persistence, corrected/new snapshot creation, approval persistence, terminal rejected/approved read-only posture, prior rejected snapshot immutability, and read-only Reviewer Work Queue posture.
- No production, staging, Railway, `salvardata.com`, or non-loopback mutation target was used.
- Local V2 mutation E2E previously passed: `1 passed` in about 2.6 minutes on localhost only.
- Patient correction-loop status messaging: `npm test` 73 passed, lint passed, typecheck passed.
- Reviewer immutable snapshot UX: `npm test` 75 passed, lint passed, typecheck passed.
- Audit bundle/manifest visibility: `npm test` 76 passed, lint passed, typecheck passed.
- Outcome Evidence Readiness backend/demo-data validation passed in the completed prior slice with targeted backend tests, broader backend tests, and `git diff --check`; the frontend display was validated with patient-detail tests, typecheck, lint, build, and `git diff --check`.
- Product clarity checkpoint: `git diff --check` passed; trailing whitespace scan passed.
- Staging and production mutation tests were intentionally skipped.

## What A Demo Operator Should Show

Use [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md) for the concise live presenter script.

- Patient detail correction-loop status messaging.
- Outcome Evidence Readiness on patient detail when persisted packet evidence is available, including synthetic ACCESS track, metric, baseline/follow-up, readiness status, completeness, and care update milestone.
- Latest actionable packet explanation.
- Terminal historical snapshot read-only posture.
- Reviewer Work Queue immutable/read-only posture.
- Audit bundle and manifest explanation.
- Local-only controls only when running the localhost mutation demo.
- Production V1 remains read-only.

## What Not To Show Or Do

- Do not mutate production demo data.
- Do not run mutation E2E against `https://access2.salvardata.com`.
- Do not run mutation E2E against `https://api.salvardata.com/api/v1`.
- Do not target `railway.app` or `up.railway.app` production hosts.
- Do not use seed/reset as a Railway startup command.
- Do not imply superuser override approval is ready.
- Do not imply staging mutation E2E is ready.
- Do not imply production mutation support.
- Do not imply Outcome Evidence Readiness is a CMS submission, claims submission, billing workflow, or real PHI workflow.

## Demo Readiness Checklist

- [ ] Local backend is healthy.
- [ ] Local frontend is healthy.
- [ ] Safe local env vars are set.
- [ ] Local mutation E2E frontend and API targets are both loopback-only.
- [ ] Local seed/reset completed.
- [ ] Local demo patient ID recorded.
- [ ] No production URLs appear in env vars.
- [ ] Operator can explain the immutable rejected packet.
- [ ] Operator can explain the corrected new snapshot.
- [ ] Operator can explain Outcome Evidence Readiness as read-only packet evidence readiness, not CMS/claims/billing submission.
- [ ] Operator can explain audit bundle and manifest verification.
- [ ] Production read-only posture is understood.

## Known Troubleshooting

- `frontend/.env.local` backend URL mismatch: confirm it points to `http://localhost:8000/api/v1`.
- Stale Next.js cache with `.next` module or page `ENOENT` errors: stop the local frontend, clear only local generated `frontend\.next`, restart the frontend, then reopen `/login`.
- Frontend port mismatch: confirm whether the current frontend is on `3000` or `3001`, then set `ACCESS2_E2E_BASE_URL` accordingly.
- Cold local Next.js route compilation or timeout before approval assertions: warm `/login`, the seeded patient detail page, and `/audit-readiness` on the loopback frontend, set `ACCESS2_E2E_API_BASE_URL=http://localhost:8000/api/v1`, then rerun only the localhost-gated command. In the May 16, 2026 rehearsal, the Docker frontend on port `3000` was slow but valid after clearing stale `.next` output; port `3001` did not remain reachable.
- Playwright spawn `EPERM`: restart the local shell or Playwright process and rerun only the localhost-gated command.
- Missing safe localhost env vars: the local mutation E2E intentionally skips or refuses to run.
- Production-like URL blocked by host guard: stop and correct the target before running any local mutation command.
- Local E2E intentionally skipped when env vars are not set: set the explicit localhost gates only when running against disposable local data.

## Current Limitations

- No staging environment is provisioned.
- No staging seed/reset implementation exists.
- No staging mutation E2E exists.
- No production mutation E2E exists.
- No superuser override approval is ready.
- No broad workflow mutation controls are ready.

## Recommended Next Options

Option A: Stakeholder package review.

- Use [access2-stakeholder-demo-package-index.md](C:/dev/access2/docs/access2-stakeholder-demo-package-index.md) as the single stakeholder-facing entry point.
- Best if preparing external review or deciding whether the proof chain is clear.

Option B: V1 production demo hardening.

- Keep production read-only.
- Improve docs, copy, or reliability only if stakeholder review exposes a concrete gap.

Option C: Isolated staging planning.

- Only after separate staging or preview infrastructure is explicitly approved.
- No mutation E2E in this handoff and no production mutation.

Option D: Hold new work.

- Keep the current V1/V2 package stable and collect feedback.

## Recommended Next Slice

Recommend: one local-only V2 operator rehearsal using the operator clarity checkpoint above and [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md).

Keep any follow-up docs-only or copy-only unless a real localhost demo blocker appears, and keep V2 mutation localhost-only. This does not authorize staging, Railway, or production mutation.
