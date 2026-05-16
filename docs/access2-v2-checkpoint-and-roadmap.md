# ACCESS2 V2 Checkpoint And Roadmap

## Purpose

This checkpoint summarizes where ACCESS2 V2 stands after the local correction-loop work and defines the safest next slices. It is a planning and handoff document only. It does not authorize production mutation testing, shared demo-data mutation, override approval, broad workflow controls, deployment changes, or backend startup command changes.

## Current State

ACCESS2 V1 remains the production-safe demo posture:

- Production frontend: `https://access2.salvardata.com`
- Production backend API: `https://api.salvardata.com/api/v1`
- Production demo data is synthetic-only.
- Production E2E remains read-only.
- Demo Patient 3 remains the read-only rejected-posture scenario.
- The backend startup command remains `bash scripts/render-start.sh`.

ACCESS2 V2 is proven locally as a controlled correction loop:

```text
original pending snapshot -> assign reviewer -> reject with reason -> corrected synthetic outcome/evidence -> create new immutable review packet snapshot -> approve corrected pending snapshot -> old rejected packet preserved/read-only -> approved packet terminal/read-only
```

The local proof strengthens the core ACCESS2 product requirement: interventions must connect to measurable outcomes and defensible evidence. A rejected packet is not refreshed or edited. Corrected current evidence is captured by creating a new immutable review packet snapshot, and that corrected packet can be approved locally while historical rejected/approved packets remain available as read-only audit evidence.

## Post-Demo Package Checkpoint - May 16, 2026

ACCESS2 now has a complete demo and positioning package for the current release posture:

- V1 production demo readiness is complete for external read-only walkthroughs using synthetic data at `https://access2.salvardata.com`.
- V1 production E2E remains documented at `8 passed, 2 skipped, 0 failed`; the two skips remain intentional mutation-path skips.
- V2 local demo readiness is complete for localhost-only correction-loop demonstration.
- The clean V2 local presenter rehearsal was recorded with loopback-only targets and preserved immutable rejected snapshot history.
- The product/release positioning doc now explains the cross-version story: V1 production is read-only, V2 mutation is localhost-only, and staging mutation waits for explicit isolated staging approval.

Current proof boundaries:

- Production proves read-only evidence visibility, review-packet posture, approved audit bundle posture, and manifest verification.
- Localhost V2 proves assignment, rejection, corrected/new snapshot creation, corrected approval, `audit_bundle.available=true`, and preserved rejected snapshot history.
- No production, Railway, staging, `https://`, or non-loopback mutation target is approved.

Current non-goals:

- No production mutation.
- No staging mutation.
- No Railway mutation.
- No override approval UI.
- No EHR/FHIR, billing, AI, predictive analytics, real CMS submission, or real PHI workflow.

Staging prerequisites before any mutation expansion:

- Explicit approval for an isolated staging or preview environment.
- Separate frontend, API, database, tenant, credentials, and synthetic seed data from production.
- Deterministic seed/reset ownership and teardown.
- Fail-closed mutation host guards that continue to refuse production/custom-domain/Railway-like targets.
- Mutation E2E kept separate from production read-only E2E.

Recommended next options:

- Option A - Stakeholder-facing demo package review: use [access2-stakeholder-demo-package-index.md](C:/dev/access2/docs/access2-stakeholder-demo-package-index.md) to rehearse the combined story without new code.
- Option B - V1 production demo hardening: keep production read-only and improve only operator reliability, copy clarity, or validation documentation if a real demo-day gap appears.
- Option C - Isolated staging preparation: use existing staging docs only after isolated staging or preview infrastructure is explicitly approved; do not run mutation E2E yet.
- Option D - Small read-only product clarity: improve docs or UI copy only where it directly clarifies the ACCESS2 proof chain without adding workflow mutation.

Recommended next slice: run a stakeholder-facing demo package review using [access2-stakeholder-demo-package-index.md](C:/dev/access2/docs/access2-stakeholder-demo-package-index.md). Keep it docs-only unless the review exposes a concrete demo blocker.

## What V2 Proves Today

- A reviewer can reject the latest `pending_review` packet with a required reason in a controlled local flow.
- A reviewer can be assigned to the latest `pending_review` packet in a controlled local flow.
- A new immutable review packet snapshot can be created from current evidence after rejection.
- The corrected latest `pending_review` packet can be approved locally when the persisted review checklist has no missing evidence.
- The approved snapshot becomes terminal/read-only and audit-bundle-ready.
- Old `packet_json` and `packet_markdown` remain preserved for rejected, approved, and historical packets.
- Local seed/reset can create a visible synthetic correction story using a later `systolic_bp` outcome and post-rejection care update.
- Local mutation E2E validates the chain from assignment to rejection to corrected evidence to new pending snapshot to approved terminal snapshot.
- Reviewer Work Queue remains read-only; mutation controls stay patient-detail-only.
- Local mutation E2E is gated by `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` and refuses production/Railway-like hosts.
- The shared mutation E2E host guard exists and blocks production/custom-domain and Railway-like targets by default.
- The staging seed/reset dry-run guard exists for non-secret future staging input validation only.
- Production remains read-only and synthetic/demo-only.
- No superuser override approval was added.
- No production mutation testing was run.

## Production-Ready Versus Local-Only

Production-ready posture:

- V1 read-only evidence review, audit-readiness visibility, approved audit bundle download, and manifest verification.
- Synthetic production demo patients and read-only production E2E.
- Persisted immutable snapshot reads, audit bundle reads, and manifest verification against persisted snapshot data.
- Tenant scoping and service-owned business logic remain required invariants.

Local-only V2 posture:

- Reviewer assignment mutation.
- Reviewer rejection mutation.
- New snapshot creation after rejected or no-snapshot posture.
- Post-rejection synthetic correction evidence setup.
- Local mutation E2E for the correction loop.

These V2 mutation paths must remain local-only until a disposable staging or preview target exists with isolated data, reset/reseed ownership, explicit host guards, and documented teardown.

## Completed V2 Slices

- Controlled reviewer rejection: patient-detail-only, latest `pending_review` only, required decision note, terminal states protected, immutable packet content preserved.
- Controlled reviewer assignment: patient-detail-only, latest `pending_review` only, backend rejects terminal snapshots, audit event recorded, immutable packet content preserved.
- Controlled new snapshot creation: patient-detail-only, creates a new immutable packet from current evidence, does not refresh or mutate old packets.
- Controlled corrected-packet approval: patient-detail-only, latest `pending_review` only, requires persisted review checklist completeness, records approval through the existing review path, and leaves approved snapshots terminal/read-only.
- V2 correction-loop E2E: local-only flow validates assignment, rejection, corrected evidence, new pending snapshot, corrected approval, preserved old rejected packet, approved terminal/read-only posture, and read-only queue posture.
- Local seed proof story: disposable synthetic marker creates or repairs a local scenario with post-rejection correction evidence.
- Staging seed/reset dry-run guard: validates non-secret future staging inputs only, refuses production/Railway-like targets, and performs no seed, reset, database, network, or mutation E2E operation.
- Demo/runbook docs: local-only correction-loop script, troubleshooting, and production don’ts are documented.
- Product clarity polish after the correction-loop proof:
  - V2 correction-loop demo script is polished for a 5-10 minute operator walkthrough.
  - Patient detail explains latest actionable packet, historical packets, corrected snapshots, and local-only/read-only posture.
  - Reviewer Work Queue explains immutable snapshot review posture and remains read-only.
  - Patient detail explains that audit bundles export immutable snapshot evidence and manifests verify exported artifacts.

## Latest Known Validation

```text
backend targeted approval tests: 3 passed
frontend npm test: 55 passed
lint: passed
typecheck: passed
local mutation E2E: May 16, 2026 rehearsal passed with 1 passed (10.6m), localhost only
git diff --check: passed
```

The May 16, 2026 local rehearsal used frontend `http://localhost:3000` and API `http://localhost:8000/api/v1`. The disposable local patient reached an approved latest snapshot, `audit_bundle.available=true`, and prior rejected terminal snapshots remained visible in backlog/history.

## V2 Local Demo Readiness Checkpoint - May 16, 2026

Local V2 demo readiness is complete for localhost-only demonstration. This means ACCESS2 has enough local proof, runbook coverage, and presenter material to rehearse and show the V2 correction loop on a disposable local environment.

This checkpoint is documentation-only. It does not approve staging mutation, Railway mutation, production mutation, production demo-data mutation, or any non-loopback mutation testing.

Completed proof points:

- Local-only correction-loop rehearsal passed.
- Local mutation E2E passed with `npm run test:e2e:local-mutation`: `1 passed (10.6m)`.
- The rehearsal used frontend `http://localhost:3000` and API `http://localhost:8000/api/v1`.
- The disposable local patient reached an approved latest snapshot.
- `audit_bundle.available=true` for the approved latest snapshot.
- Prior rejected terminal snapshots remained in backlog/history and were not edited or overwritten.
- The local E2E harness was hardened for slow cold local Next.js/Docker timing.
- The operator-facing one-page script now exists.

Completed demo assets:

- Handoff index: [access2-v2-local-demo-handoff-index.md](C:/dev/access2/docs/access2-v2-local-demo-handoff-index.md)
- Technical handoff: [access2-v2-demo-readiness-handoff.md](C:/dev/access2/docs/access2-v2-demo-readiness-handoff.md)
- Detailed correction-loop guide: [access2-v2-correction-loop-demo.md](C:/dev/access2/docs/access2-v2-correction-loop-demo.md)
- Operator-facing script: [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md)
- Planning/checkpoint routing: [access2-v2-planning.md](C:/dev/access2/docs/access2-v2-planning.md) and this roadmap.

Still not done:

- No isolated staging environment exists yet.
- No staging mutation E2E exists.
- No production mutation is approved.
- No Railway mutation is approved.
- No override approval UI exists.
- No EHR/FHIR integration exists.
- No billing integration exists.
- No real PHI is used.
- V1 production remains read-only.

Recommended next options:

- Option A - Live manual local demo rehearsal: use the operator script to rehearse the demo manually. Do not add code unless blockers are found. Best for preparing a stakeholder walkthrough.
- Option B - Package V2 local demo handoff: create a compact handoff index or release note linking the three demo docs. Best when handing the repo to another operator or reviewer.
- Option C - Provision isolated staging: use the existing staging provisioning docs only after an isolated staging or preview environment is explicitly approved. No production mutation.
- Option D - Return to V1 production demo hardening: keep production read-only and improve demo-day reliability, copy, or evidence explanation. Best for external demos that do not require V2 mutation.

Recommended next step: run one manual local presenter rehearsal using the operator script, then package the V2 local demo handoff if the talk track is stable.

## V2 Product Clarity Checkpoint

This checkpoint captures completed non-staging product clarity work after the localhost V2 correction-loop proof. It is documentation and handoff context only. It does not authorize backend behavior changes, new routes, new mutation controls, staging implementation, production mutation testing, Railway configuration changes, or backend startup changes.

Current clarity status:

- The local correction loop is proven: assignment -> rejection with reason -> immutable rejected packet -> corrected evidence -> new pending snapshot -> approval -> terminal/read-only posture.
- The V2 correction-loop demo script is polished and operator-ready.
- Patient detail explains correction-loop state, including latest actionable packet, historical rejected/approved packets, corrected snapshots, and local-only gated behavior.
- Reviewer Work Queue explains immutable/read-only snapshot posture and remains read-only.
- Audit bundle and manifest copy explains that the snapshot captures evidence, the bundle exports it, and the manifest verifies what was exported.
- Production remains V1 read-only and synthetic/demo-only.

Completed product clarity slices:

- `Polish V2 correction loop demo script`
- `Add patient correction loop status messaging`
- `Clarify reviewer immutable snapshot UX`
- `Polish audit bundle manifest visibility`

What these slices improved:

- Operator understanding of the latest actionable `pending_review` packet.
- Operator understanding of historical approved/rejected packets as terminal audit evidence.
- Clearer explanation that immutable `packet_json` and `packet_markdown` are not overwritten or refreshed.
- Clearer explanation that corrected evidence creates a new immutable snapshot rather than repairing an old rejected packet.
- Clearer explanation that audit bundles export persisted snapshot evidence and readiness reasons.
- Clearer explanation that manifests verify exported artifacts against persisted snapshot data.
- Clearer read-only posture for Reviewer Work Queue and production V1.

What did not change:

- No backend behavior changed.
- No new mutation controls were added.
- No new routes were added.
- No production mutation testing was run.
- No staging implementation was added.
- No Railway configuration changed.
- No superuser override approval was added.
- No broad workflow mutation controls were added.

Recent product clarity validation:

- Patient correction-loop status messaging: `npm test` 73 passed, lint passed, typecheck passed.
- Reviewer immutable snapshot UX: `npm test` 75 passed, lint passed, typecheck passed.
- Audit bundle/manifest visibility: `npm test` 76 passed, lint passed, typecheck passed.
- `git diff --check` passed for each slice with only normal CRLF warnings.
- Local mutation E2E was skipped in recent copy-only slices when safe localhost env/listeners were unavailable.
- Staging and production mutation tests were intentionally skipped.

Recommended next options:

- Option A: Live manual local demo rehearsal using [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md). No new code unless blockers are found.
- Option B: Package V2 local demo handoff with a compact index or release note linking the readiness handoff, detailed guide, and operator script.
- Option C: Return to staging only if isolated staging infrastructure is ready. Use [access2-v2-staging-provisioning-checklist.md](C:/dev/access2/docs/access2-v2-staging-provisioning-checklist.md) first.
- Option D: Return to V1 production demo hardening while keeping production read-only.

Recommended next slice:

`Run manual local V2 presenter rehearsal`

Rationale:

- Lowest risk.
- Docs-only.
- Uses the completed local proof and presenter script before any staging or broader V2 work.
- Confirms the talk track and operator flow without changing production posture.

The handoff now lives in [access2-v2-demo-readiness-handoff.md](C:/dev/access2/docs/access2-v2-demo-readiness-handoff.md). It summarizes the localhost-only correction-loop proof, demo prerequisites, operator checklist, current limitations, and the local rehearsal path without authorizing staging or production mutation.

Explicitly defer:

- Superuser override approval.
- Broad workflow mutation controls.
- Staging mutation E2E.
- Production mutation E2E.
- Production demo data mutation.

## What Remains Before Production-Grade V2

- Production-grade mutation governance: define who may assign, reject, approve, and create snapshots in a real deployment posture.
- Isolated staging or preview environment: separate frontend/API/database/tenant from shared production demo data.
- Reset/reseed strategy outside localhost: deterministic disposable targets, pre-test state restoration, post-test verification, and teardown guidance.
- Stronger audit-role permissions if needed: keep this narrow and avoid a broad role-management redesign.
- A production-safe promotion plan that keeps V1 production read-only until mutation governance and disposable validation are proven.
- Documentation alignment so local V2 guidance does not drift from production V1 read-only guardrails.

## Highest Current Risks

- Accidentally mutating shared production demo data.
- Confusing creation of a new immutable snapshot with refreshing or editing an old packet.
- Adding override behavior before rejection/correction/approval governance is production-safe.
- Running mutation E2E against an insufficiently isolated staging or Railway target.
- Drifting docs between local V2 mutation behavior and read-only production V1 demo behavior.
- Expanding into broad workflow mutation or generic case management before the audit proof chain is stable.

## Intentionally Out Of Scope

Do not implement these as part of the checkpoint or next narrow roadmap slice:

- Superuser override approval.
- Production mutation E2E.
- Mutation of shared production demo data.
- Broad intervention/task/evidence editing UI.
- Audit-readiness queue mutation controls.
- Railway configuration changes.
- Backend startup command changes.
- Real PHI, secrets, EHR/FHIR integration, billing, predictive analytics, or broad admin workflows.

## V2 Staging Decision Point

This decision point is documentation only. It does not authorize staging setup, staging seed/reset implementation, staging mutation E2E, production mutation testing, Railway configuration changes, backend startup changes, or superuser override approval.

Current status:

- The localhost correction-loop proof is complete.
- Corrected-packet approval is locally proven.
- Old immutable rejected and approved packets remain preserved.
- The mutation E2E host guard exists and fails closed for production/Railway-like hosts.
- The staging seed/reset dry-run guard exists and validates non-secret staging input shape only.
- Production remains read-only.

Decision options:

- Option A: Isolated staging environment setup.
  Best if the next goal is production-grade V2 promotion or validation outside localhost. Requires separate staging database, staging frontend/backend URLs, staging-only credentials, synthetic-only data, and no production demo mutation. This must happen before any staging mutation E2E execution and must not reuse the production database, production demo data, or production Railway configuration.
- Option B: Staging seed/reset implementation.
  Best only after Option A details are known. It must follow [access2-v2-staging-seed-reset-contract.md](C:/dev/access2/docs/access2-v2-staging-seed-reset-contract.md), be idempotent or safely resettable, preserve terminal historical `packet_json` and `packet_markdown` unless a whole disposable staging scenario is explicitly dropped/reset, be preceded by the dry-run guard, and never run against production.
- Option C: Staging mutation E2E skeleton.
  Best only after the staging environment and seed/reset contract are satisfied. It should initially skip or fail closed unless an explicit staging gate and exact host allowlist are present. It must remain separate from production read-only E2E and must not target `access2.salvardata.com`, `api.salvardata.com`, `railway.app`, or `up.railway.app`.
- Option D: Hold staging and return to product workflow features.
  Best if staging infrastructure is not ready. Candidate work should stay non-mutating or tightly scoped to the ACCESS proof chain, such as UX clarity, audit-bundle display/read-only enhancements, docs/demo polish, or other product workflow improvements that do not add broad mutation controls prematurely.

Recommended decision:

- Choose Option A first if the goal is production-grade V2 promotion.
- Choose Option D if there is no immediate isolated staging infrastructure available.
- Do not choose Option B or Option C until Option A environment details are known.
- Do not implement superuser override approval yet.

Go/no-go criteria before Option A:

- Confirm the desired staging host strategy: Railway preview, separate Railway services, or another host.
- Confirm a separate staging database.
- Confirm staging frontend and backend domain names.
- Confirm staging-only credential handling.
- Confirm synthetic-only seed/reset approach.
- Confirm no production configuration or production data mutation.

Open questions:

- What exact staging URL strategy should ACCESS2 use?
- Will staging live on Railway preview, separate Railway services, or another provider?
- What database identity check can the dry-run guard use?
- Should staging use a new gate variable separate from `ACCESS2_ENABLE_LOCAL_MUTATION_E2E`?
- Should disposable staging scenarios be cleaned or versioned?
- Who is the intended V2 reviewer/operator role in staging?

Non-goals for this decision point:

- No production mutation E2E.
- No production demo data mutation.
- No superuser override approval.
- No broad workflow mutation controls.
- No staging seed/reset implementation.
- No staging mutation E2E skeleton.
- No Railway config changes.

Suggested next prompt:

- If staging infrastructure is available: `Document isolated staging environment setup plan`.
- If staging infrastructure is not available: `Select next non-staging ACCESS2 V2 product workflow slice`.

## Non-Staging Product Workflow Decision

The current non-staging product decision is documented in [access2-v2-product-workflow-next-slice.md](C:/dev/access2/docs/access2-v2-product-workflow-next-slice.md). Recommendation: choose Candidate A, V2 correction-loop demo script polish, before product UI polish. This is the lowest-risk next slice because it is docs-only, captures the completed localhost proof chain, improves operator storytelling, and avoids new mutation behavior.

Secondary recommendation: Candidate B, patient-detail correction-loop status messaging, can follow after the demo script if product UI clarity is still the priority.

Explicitly defer superuser override approval, broad workflow mutation controls, staging mutation E2E, production mutation E2E, and production demo data mutation.

## Recommended Next Implementation Candidate

The next smallest implementation candidate depends on the decision above. If staging infrastructure is available, start with Option A: isolated staging environment setup planning. If staging infrastructure is not available, hold staging and choose Option D: a non-staging ACCESS2 V2 product workflow slice.

Recommended boundaries:

- Keep the current corrected approval proof localhost-only.
- Define minimum requirements for a disposable staging or preview target before any non-local mutation E2E.
- Preserve rejected/approved/historical packet immutability and read-only production demo posture.
- Keep Reviewer Work Queue read-only.
- Keep production E2E read-only and production mutation tests skipped.
- Keep local seed/reset and gated local E2E validation separate from production demo data.
- Keep backend validation in services and routes thin for any future workflow mutation.

This should wait until the checkpoint is accepted because moving mutation proof beyond localhost requires stronger data isolation and reset ownership than the current shared production demo posture provides.

## Why Override Approval Should Still Wait

Override approval can approve a packet despite readiness gaps. That is useful for exception handling, but it is also the riskiest review mutation because it can create an audit-ready or exportable posture from incomplete evidence. ACCESS2 has now proven normal approval of a corrected pending packet in a disposable local environment; override approval should still wait for separate governance, permissions, audit wording, and validation.

## Reference Documents

- [access2-v2-planning.md](C:/dev/access2/docs/access2-v2-planning.md)
- [access2-stakeholder-demo-package-index.md](C:/dev/access2/docs/access2-stakeholder-demo-package-index.md) - stakeholder-facing reading order, presenter order, proof boundaries, and next decision.
- [access2-v2-local-demo-handoff-index.md](C:/dev/access2/docs/access2-v2-local-demo-handoff-index.md) - entry point for the localhost-only V2 demo package.
- [access2-v2-correction-loop-demo.md](C:/dev/access2/docs/access2-v2-correction-loop-demo.md)
- [access2-v2-demo-readiness-handoff.md](C:/dev/access2/docs/access2-v2-demo-readiness-handoff.md) - consolidated localhost-only V2 demo readiness handoff and rehearsal checklist.
- [access2-v2-product-workflow-next-slice.md](C:/dev/access2/docs/access2-v2-product-workflow-next-slice.md) - non-staging product workflow decision and recommended next demo-script slice.
- [access2-v2-isolated-staging-environment-plan.md](C:/dev/access2/docs/access2-v2-isolated-staging-environment-plan.md) - required staging boundary plan before seed/reset implementation or staging mutation E2E.
- [access2-v2-staging-provisioning-checklist.md](C:/dev/access2/docs/access2-v2-staging-provisioning-checklist.md) - operator checklist before creating or validating isolated V2 staging.
- [access2-v2-staging-seed-reset-contract.md](C:/dev/access2/docs/access2-v2-staging-seed-reset-contract.md) - includes the dry-run guard operator command: `py -3 backend\scripts\check_staging_v2_seed_reset_contract.py`
- [access2-v2-staging-env-template.md](C:/dev/access2/docs/access2-v2-staging-env-template.md) - placeholder environment values for the staging dry-run guard.
- [access2-demo-data-recreation-checklist.md](C:/dev/access2/docs/access2-demo-data-recreation-checklist.md)
- [access2-v1-demo-handoff-summary.md](C:/dev/access2/docs/access2-v1-demo-handoff-summary.md)
- [access2-v1-scope-control.md](C:/dev/access2/docs/access2-v1-scope-control.md)
