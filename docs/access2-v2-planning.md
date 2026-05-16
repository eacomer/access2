# ACCESS2 V2 Planning Outline

This document is a planning artifact only. It does not authorize implementation by itself, and it must not change the ACCESS2 V1 production demo posture until a separate V2 implementation slice is explicitly approved.

ACCESS2 V2 should extend the V1 evidence chain carefully:

signal -> escalation -> intervention -> outcome -> evidence -> case summary -> immutable review packet snapshot -> assignment -> approval/rejection -> audit bundle -> manifest verification

The core product question remains whether ACCESS2 can prove that chronic care interventions led to measurable outcomes and that the evidence was reviewed through a defensible audit lifecycle.

## V1 Recap

### Complete

- Production frontend is available at `https://access2.salvardata.com`.
- Backend API is available at `https://api.salvardata.com/api/v1`.
- Production E2E baseline is `8 passed, 2 skipped, 0 failed`.
- Demo data is synthetic-only and intended for CMS ACCESS-aligned workflow demonstration.
- The V1 demo path covers login, audit-readiness visibility, patient evidence chain visibility, immutable review packet snapshots, persisted readiness reasons, audit bundle export, and manifest verification.
- Audit bundle reads use persisted snapshot, evidence, and event metadata rather than rebuilding packet content during audit reads.
- Manifest verification validates exported audit bundles against persisted snapshot data.
- Tenant scoping remains a required invariant across workflow objects.

### Intentionally read-only

- The V1 frontend demo posture is read-only for workflow mutation.
- No frontend controls are exposed for approve, reject, assign, create-snapshot, override approval, or audit-bundle export mutation as uncontrolled workflow actions.
- The two expected production E2E skips remain:
  - Demo Patient 3 reviewer rejection through UI.
  - Demo Patient 4 superuser override approval through UI.
- Rejection and override postures are represented in synthetic seeded demo data for evidence review, but they are not currently operated through frontend mutation controls.

### Must not regress

- Do not introduce real PHI.
- Do not commit secrets or production credentials.
- Do not break the V1 read-only demo posture accidentally.
- Do not change Railway deployment configuration.
- Do not change the backend startup command, which should remain `bash scripts/render-start.sh`.
- Do not leave seed commands as Railway startup commands.
- Do not mutate immutable review packet snapshots.
- Do not rebuild persisted `packet_json` or `packet_markdown` during audit reads.
- Do not weaken tenant scoping or patient consistency across linked records.
- Do not replace thin routes and service-owned business logic with route-level workflow logic.

## V2 Product Question

What is the first controlled workflow operation ACCESS2 should support after V1?

The first V2 operation should be narrow enough to preserve the V1 production baseline while proving that ACCESS2 can safely transition from read-only evidence display into an auditable workflow action.

## Candidate V2 Options

### Reviewer rejection action

Allow a reviewer to reject an immutable review packet snapshot with a required rejection reason.

Evaluation:

- Directly maps to an existing expected skipped production E2E test for Demo Patient 3.
- Already represented in seeded synthetic demo data.
- Has a clear audit contract: who rejected, when, why, which snapshot was rejected, and what state changed afterward.
- Strengthens the review lifecycle without adding broad workflow mutation.
- Safer than approval override because rejection blocks or returns the case for correction instead of creating a payment-ready posture.

### Superuser override approval action

Allow a privileged user to approve a snapshot despite unresolved readiness concerns.

Evaluation:

- Maps to the second expected skipped production E2E test for Demo Patient 4.
- Useful for demonstrating exception handling.
- Higher risk than rejection because it can move a case toward audit-ready or exportable posture despite gaps.
- Should wait until the rejection path proves the frontend, backend, audit event, and test pattern for controlled mutation.

### Controlled audit bundle export action

Expose a controlled frontend action for exporting an approved audit bundle.

Evaluation:

- Important to the end-to-end evidence story.
- Requires careful treatment of successful-export event logging and failure behavior.
- Should not be first if approval/rejection lifecycle operation is still read-only.
- Safer after the review state machine and event recording are proven through rejection.

### Reviewer assignment action

Allow assigning a snapshot to a reviewer.

Evaluation:

- Useful operationally, but less central to proving that interventions led to measurable outcomes.
- Can introduce user and permission assumptions that are broader than the first V2 slice needs.
- Should be deferred unless assignment is required to safely gate reviewer rejection.

### Intervention/task update action

Allow care teams to update intervention or task status.

Evaluation:

- Moves ACCESS2 closer to operational care management.
- Broader than the V2 first operation because it touches earlier workflow-chain state and may require task ownership, due dates, status rules, and additional UI.
- Risks expanding into generic case management if not tightly scoped.

### Outcome/evidence capture improvement

Improve how outcomes and supporting evidence are captured or attached.

Evaluation:

- Strongly aligned with the principle that ACCESS2 must prove interventions led to measurable outcomes.
- Likely valuable after V1, but can become larger than a first controlled mutation slice.
- Should be planned as a separate evidence-quality slice after the review lifecycle has a safe mutation pattern.

## Recommendation

The smallest safe V2 slice is:

**Controlled reviewer rejection action**

This is the best first V2 operation because it maps directly to an existing skipped E2E test, is already represented in seeded synthetic demo data, has clear audit requirements, and is safer than override approval. It proves that ACCESS2 can support a controlled review lifecycle action without opening broad workflow mutation or changing the product into a general case-management tool.

Reviewer rejection also creates a clear bridge from V1 read-only evidence posture to V2 controlled mutation: only the correct snapshot state should expose the action, the reason must be required, and the result must be auditable without mutating immutable packet content.

## Current Implementation Status

The first controlled V2 workflow operation is now implemented as reviewer rejection of a review packet snapshot.

- Backend uses the existing review endpoint: `PATCH /api/v1/reports/access-review-packet/snapshots/{snapshot_id}/review`.
- The frontend uses a reject-only proxy route at `/review-packet-snapshots/{snapshot_id}/reject`.
- The proxy sends `review_status="rejected"` and `decision_note` as the required, trimmed rejection reason.
- The patient-detail page exposes the control only in the review packet backlog for the latest snapshot when `review_status == "pending_review"`.
- Approved, rejected, and historical snapshots remain read-only.
- The audit-readiness queue remains read-only and does not expose reject, approve, override, assignment, export, or create-snapshot mutation controls.

Backend guardrails remain part of the contract:

- Rejection requires a non-empty reason.
- Whitespace-only reasons are invalid.
- Terminal review states cannot be rewritten.
- Tenant scoping is enforced by backend snapshot lookup and review update logic.
- Snapshot `packet_json` and `packet_markdown` remain immutable.
- Rejected snapshots continue to block audit bundle generation and manifest verification.

The next controlled V2 slice is implemented as approved-snapshot audit bundle export/download controls on patient detail.

- Backend export semantics were reused; no new backend export route or workflow state transition was added.
- The frontend uses the existing authenticated proxy route at `/audit-bundles/{snapshotId}/{format}` for JSON, Markdown, and PDF bundle downloads.
- Patient detail exposes audit bundle download actions only for approved snapshots that can use the persisted audit bundle export endpoints.
- Pending, rejected, and non-export-ready snapshots remain read-only with explanatory copy.
- Audit-readiness and reviewer work queue remain read-only and do not expose approve, reject, override, assignment, create-snapshot, or export controls.
- Successful downloads may record `audit_bundle_exported` events through the existing backend export endpoints; manifest verification behavior remains unchanged.

The controlled reviewer assignment UI is implemented and locally validated as a patient-detail-only mutation control.

- Patient detail exposes reviewer assignment only in the review packet backlog for the latest snapshot when `review_status == "pending_review"`.
- Approved, rejected, and historical snapshots remain read-only; assignment does not approve, reject, export, or mutate snapshot packet content.
- Reviewer Work Queue remains read-only and does not expose assignment mutation controls.
- The frontend assignment proxy route uses the existing backend route: `PATCH /api/v1/reports/access-review-packet/snapshots/{snapshot_id}/assignment`.
- The assignment UI now posts `assigned_reviewer_user_id` directly. The proxy accepts both `assignedReviewerUserId` and `assigned_reviewer_user_id` for compatibility, but forwards only `assigned_reviewer_user_id` to the backend.
- The proxy fails closed if a successful backend response does not echo the requested `assigned_reviewer_user_id`.
- The UI shows deterministic success and error copy, including `Reviewer assigned.` after a successful assignment.
- Existing backend behavior records `snapshot_assigned` audit events and preserves immutable `packet_json` and `packet_markdown`.
- Local mutation E2E passed with `npm run test:e2e:local-mutation`, result `1 passed in 43.1s`.
- The passing local E2E assigned and then rejected the disposable local latest `pending_review` snapshot through the patient UI, asserted `Reviewer assigned.` before backend polling, verified `assigned_reviewer_user_id`, and kept production mutation testing skipped.

The controlled new review packet snapshot UI is implemented as a patient-detail-only creation control.

- This creates a new immutable snapshot from the current live case summary, review packet, and evidence state.
- Existing rejected, approved, and historical snapshots keep their persisted `packet_json` and `packet_markdown`.
- The frontend uses an authenticated proxy route at `/review-packet-snapshots/patients/{patient_id}/create`.
- The proxy calls the existing backend route: `POST /api/v1/reports/access-review-packet/{patient_id}/snapshots`.
- Patient detail exposes `Create new review packet snapshot` only when the latest posture has `next_step.action == "create_snapshot"` and either the latest snapshot is rejected or no snapshot exists yet.
- Approved and `pending_review` latest snapshots do not expose the control; historical snapshots remain read-only.
- Reviewer Work Queue remains read-only and does not expose approve, reject, assign, export, override, or create-snapshot controls.
- The UI shows deterministic success and error copy, including `New review packet snapshot created.` after a successful creation.
- Local mutation E2E now covers assignment, rejection, and creation of a new latest `pending_review` snapshot while verifying the old rejected snapshot remains preserved and read-only.
- Fresh local stabilization result: `npm run test:e2e:local-mutation` passed with `1 passed (2.2m)` against a clean local frontend on `http://localhost:3001` after clearing stale `.next` state. The run proved latest rejected snapshot -> create new snapshot -> new latest `pending_review`; old rejected snapshot stayed visible/read-only; assignment and rejection buttons were visible only again for the new latest pending snapshot.
- Production mutation E2E remains skipped; do not run this mutation path against shared Railway production demo data.

## ACCESS2 V2 Checkpoint — May 13, 2026

### Current Status

ACCESS2 V1 is demo-ready and production-stable in a read-only posture. The production Railway deployment at `https://access2.salvardata.com` has a documented Playwright baseline of 8 passed, 2 skipped, and 0 failed. The two skips remain intentional V1 read-only constraints for mutation workflows.

V2 has started with a local-only controlled reviewer rejection workflow. Mutation E2E coverage is intentionally gated and guarded so it can run only against safe local loopback targets. Production, Railway, and custom-domain mutation testing remain blocked.

### Recommended Project Direction

The next project phase should focus on completing the controlled V2 review workflow before adding broader product features.

Recommended sequence:

1. Document and validate the V2 mutation E2E environment guard behavior.
2. Add local-only reviewer approval mutation flow.
3. Add the correction loop after reviewer rejection.
4. Add repeatable local reset/reseed support for mutation testing.
5. Define a staging-only mutation test posture.
6. Preserve the production V1 demo as read-only until staging mutation workflows are proven.

### Working Definition of Done

ACCESS2 V2 Pilot Demo Candidate is done when the following story can be demonstrated end to end:

```text
A chronic care case has evidence gaps.
The system shows what is missing.
A review packet is generated.
A reviewer assigns/reviews the packet.
The reviewer rejects it with a reason.
The operator corrects the missing evidence.
A new immutable snapshot is generated.
The reviewer approves the corrected packet.
The approved packet exports to JSON, Markdown, and PDF.
The manifest verifies the audit bundle.
The entire chain is visible and explainable.

### V2 correction loop checkpoint

The local V2 correction loop is now documented and demoable as a localhost-only proof path:

```text
original pending snapshot -> assign reviewer -> reject with reason -> corrected synthetic outcome/evidence -> create new immutable review packet snapshot -> approve corrected pending snapshot -> old rejected packet preserved/read-only -> approved packet terminal/read-only
```

What this proves:

- The original pending packet can be assigned.
- The original pending packet can be rejected with a reason.
- ACCESS2 can handle reviewer correction without changing or rebuilding old packet content.
- A rejected packet remains historical audit evidence with its persisted `packet_json`, `packet_markdown`, decision metadata, and audit events intact.
- Corrected evidence/current state is represented by creating a new immutable review packet snapshot while preserving the old one.
- The local proof story now includes explicit synthetic post-rejection correction evidence: a later `systolic_bp` outcome with source `access2_local_v2_post_rejection_correction`, value `124`, and a care-update summary beginning `Post-rejection corrected evidence`.
- The next packet generated after that correction shows the outcome trend as `status=improved`; the older rejected packet keeps its original packet JSON and Markdown.
- The corrected latest `pending_review` snapshot can be approved through the patient-detail-only control when the persisted review checklist has no missing evidence.
- The approved snapshot becomes terminal/read-only and audit-bundle-ready.
- Assignment and rejection controls return only for the new latest `pending_review` snapshot.
- Historical rejected and approved snapshots remain visible/read-only in the patient review-packet backlog.
- Reviewer Work Queue and production E2E remain read-only; local mutation coverage is gated and fail-closed for production/Railway-like hosts.
- No superuser override approval was added.
- No production mutation testing was run.

Local-only posture:

- The correction-loop proof uses the disposable local marker `access2-local-v2-mutation:reviewer-rejection`.
- The seed and Playwright spec both require `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true`.
- If the disposable local patient already has a rejected latest snapshot, rerunning the seed adds the post-rejection correction evidence before creating the next `pending_review` snapshot.
- The local mutation E2E also inserts the same correction evidence through existing local authenticated evidence APIs after rejection and before selecting `Create new review packet snapshot`.
- The local mutation E2E then approves the corrected latest pending snapshot and verifies the approved terminal/read-only posture.
- The local mutation spec refuses configured targets containing `access2.salvardata.com`, `api.salvardata.com`, `railway.app`, or `up.railway.app`.
- Mutation E2E host refusal is centralized in `frontend/e2e/helpers/mutation-host-guard.ts`; the local mutation spec uses that shared helper while keeping `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` as the required gate.
- Latest validation used `http://localhost:3001` because port 3000 was held by stale local node processes.

Latest known validation:

```text
backend targeted approval tests: 3 passed
frontend npm test: 55 passed
lint: passed
typecheck: passed
local mutation E2E: May 16, 2026 rehearsal passed with 1 passed (10.6m), localhost only
git diff --check: passed
```

The May 16, 2026 local rehearsal used frontend `http://localhost:3000` and API `http://localhost:8000/api/v1`, required local seed/reset for the disposable marker patient, and did not run any production, staging, Railway, `salvardata.com`, or non-loopback mutation test.

### V2 local demo readiness checkpoint

Local V2 demo readiness is complete for localhost-only demonstration.

What is now complete:

- The local-only correction-loop rehearsal passed with `npm run test:e2e:local-mutation`: `1 passed (10.6m)`.
- The validated targets were frontend `http://localhost:3000` and API `http://localhost:8000/api/v1`.
- The final disposable local patient reached an approved latest snapshot and `audit_bundle.available=true`.
- Prior rejected terminal snapshots remained visible in backlog/history and were not edited or overwritten.
- The local E2E harness was hardened for slow cold local Next.js/Docker timing.
- The operator-facing one-page script now exists at [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md).

Completed demo assets:

- Technical handoff: [access2-v2-demo-readiness-handoff.md](C:/dev/access2/docs/access2-v2-demo-readiness-handoff.md)
- Detailed correction-loop guide: [access2-v2-correction-loop-demo.md](C:/dev/access2/docs/access2-v2-correction-loop-demo.md)
- Operator-facing script: [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md)
- Roadmap checkpoint: [access2-v2-checkpoint-and-roadmap.md](C:/dev/access2/docs/access2-v2-checkpoint-and-roadmap.md)

This checkpoint is documentation-only. It does not approve staging mutation, Railway mutation, production mutation, production demo-data mutation, or any non-loopback mutation testing.

Remaining explicit non-goals:

- No isolated staging environment yet.
- No staging mutation E2E.
- No production or Railway mutation.
- No override approval UI.
- No EHR/FHIR or billing integration.
- No real PHI.
- V1 production remains read-only.

Recommended next options:

- Option A - Live manual local demo rehearsal: use the operator script to rehearse the demo manually, with no new code unless blockers are found.
- Option B - Package V2 local demo handoff: create a compact handoff index or release note linking the three demo docs.
- Option C - Provision isolated staging: use existing staging provisioning docs only after an isolated staging or preview environment is explicitly approved.
- Option D - Return to V1 production demo hardening: keep production read-only and improve demo-day reliability, copy, or evidence explanation.

Recommended next step: run one manual local presenter rehearsal using the operator script, then package the V2 local demo handoff if the talk track is stable.

Intentionally out of scope:

- No production mutation testing.
- No shared Railway demo data mutation.
- No superuser override approval UI.
- No broad intervention/task/evidence editing workflow.
- No Railway configuration or backend startup command change.
- No audit-readiness queue mutation controls.

Use [access2-v2-correction-loop-demo.md](C:/dev/access2/docs/access2-v2-correction-loop-demo.md) for the manual demo script and local-only validation commands.

Use [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md) for the concise live presenter script.

Use [access2-v2-checkpoint-and-roadmap.md](C:/dev/access2/docs/access2-v2-checkpoint-and-roadmap.md) for the current V2 checkpoint, production-ready versus local-only posture, highest risks, and recommended next implementation candidate.

Use [access2-v2-product-workflow-next-slice.md](C:/dev/access2/docs/access2-v2-product-workflow-next-slice.md) for the current non-staging product workflow decision. Recommendation: pause staging unless isolated staging infrastructure is actually available, then polish the V2 correction-loop demo script before any patient-detail UI copy or other product polish.

### V2 product clarity checkpoint

The non-staging product clarity sequence after the local correction-loop proof is now complete:

- `Polish V2 correction loop demo script`
- `Add patient correction loop status messaging`
- `Clarify reviewer immutable snapshot UX`
- `Polish audit bundle manifest visibility`

Current product clarity status:

- Local correction-loop proof remains localhost-only.
- Patient detail explains the latest actionable packet, historical rejected/approved packets, corrected snapshots, and local-only gated posture.
- Reviewer Work Queue explains immutable snapshot history and remains read-only.
- Audit bundle/manifest copy explains that the snapshot captures evidence, the bundle exports it, and the manifest verifies what was exported.
- Production remains V1 read-only.

What did not change:

- No backend behavior.
- No new routes.
- No new mutation controls.
- No staging implementation.
- No production mutation testing.
- No Railway configuration changes.
- No superuser override approval.

Recent validation from the product clarity slices:

- Patient correction-loop status messaging: `npm test` 73 passed, lint passed, typecheck passed.
- Reviewer immutable snapshot UX: `npm test` 75 passed, lint passed, typecheck passed.
- Audit bundle/manifest visibility: `npm test` 76 passed, lint passed, typecheck passed.
- `git diff --check` passed for each slice with only normal CRLF warnings.
- Local mutation E2E was skipped in recent copy-only slices when safe localhost env/listeners were unavailable.
- Staging and production mutation tests were intentionally skipped.

Recommended next slice: `Document V2 demo readiness handoff`. This is the lowest-risk docs-only next step because it consolidates the demo story after product clarity polish and gives a clean checkpoint before staging or more UI work.

Use [access2-v2-demo-readiness-handoff.md](C:/dev/access2/docs/access2-v2-demo-readiness-handoff.md) for the consolidated V2 demo-ready handoff: localhost-only correction-loop proof, operator checklist, validation summary, known limitations, and the next rehearsal path. It is not a production mutation handoff or staging implementation handoff.

Use [access2-v2-staging-mutation-readiness.md](C:/dev/access2/docs/access2-v2-staging-mutation-readiness.md) for the required staging or preview environment, seed/reset, credential, host-guard, and audit-evidence checklist before any mutation testing outside localhost.

Use [access2-v2-staging-mutation-checklist.md](C:/dev/access2/docs/access2-v2-staging-mutation-checklist.md) as the final checkbox-based operator gate before staging mutation seed/reset or mutation E2E execution.

Use [access2-v2-staging-env-template.md](C:/dev/access2/docs/access2-v2-staging-env-template.md) for placeholder-only staging environment variables and command shapes before any future isolated staging mutation run.

Use [access2-v2-staging-seed-reset-contract.md](C:/dev/access2/docs/access2-v2-staging-seed-reset-contract.md) for the requirements a future isolated staging seed/reset process must satisfy before seed/reset code or staging mutation E2E is written.

Use the staging seed/reset dry-run guard command only as a non-mutating prerequisite check for future staging input safety:

```powershell
cd C:\dev\access2
py -3 backend\scripts\check_staging_v2_seed_reset_contract.py
```

This command is expected to fail safely until the required dry-run/staging guard variables are set. It does not seed, reset, connect to a database, make network calls, or authorize staging mutation E2E.

Use [access2-v2-mutation-e2e-guard-behavior.md](C:/dev/access2/docs/access2-v2-mutation-e2e-guard-behavior.md) for the current localhost mutation guard behavior, blocked production/Railway-like target rules, safe-failure expectations, and future staging allowlist posture.

Use [access2-v2-checkpoint-and-roadmap.md](C:/dev/access2/docs/access2-v2-checkpoint-and-roadmap.md) for the current staging implementation decision point. The decision tree is:

- Option A: isolated staging environment setup.
- Option B: staging seed/reset implementation.
- Option C: staging mutation E2E skeleton.
- Option D: hold staging and return to product workflow features.

Recommendation: choose Option A first if the goal is production-grade V2 promotion; choose Option D if staging infrastructure is not immediately available. Do not choose Option B or Option C until isolated staging environment details are known, and do not implement superuser override approval yet.

Use [access2-v2-isolated-staging-environment-plan.md](C:/dev/access2/docs/access2-v2-isolated-staging-environment-plan.md) for the isolated staging environment setup plan before any staging seed/reset implementation or staging mutation E2E work.

Use [access2-v2-staging-provisioning-checklist.md](C:/dev/access2/docs/access2-v2-staging-provisioning-checklist.md) as the operator checklist before creating or validating any isolated ACCESS2 V2 staging environment.

Local seed/reset command for this controlled assignment/rejection validation:

```powershell
cd C:\dev\access2\backend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:PYTHONPATH="C:\dev\access2\backend"
py -3 -m scripts.seed_local_v2_rejection_mutation
```

Local E2E command:

```powershell
cd C:\dev\access2\frontend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:ACCESS2_E2E_BASE_URL="http://localhost:3000"
$env:ACCESS2_E2E_API_BASE_URL="http://localhost:8000/api/v1"
$env:ACCESS2_E2E_ADMIN_EMAIL="admin@example.com"
$env:ACCESS2_E2E_ADMIN_PASSWORD="Admin123!"
& "C:\Program Files\nodejs\npm.cmd" run test:e2e:local-mutation
```

Troubleshooting notes:

- Run the local mutation seed as a module from `backend`: `py -3 -m scripts.seed_local_v2_rejection_mutation`.
- Set `PYTHONPATH` to `C:\dev\access2\backend` when running the seed from PowerShell.
- Local mutation E2E requires the frontend and backend running locally.
- If the disposable marker is already rejected, or if a prior E2E run timed out after a partial mutation, rerun the seed before E2E.
- The local mutation E2E may create a new latest pending snapshot after rejection; rerun the seed before another E2E cycle if local state is not at the expected latest `pending_review` starting point.
- A stale local Next.js dev cache can produce `.next` runtime errors such as `Cannot find module './570.js'`; clearing `.next` and restarting `npm run dev` resolves it.
- If an unkillable stale local frontend process keeps serving a bad cache on port 3000, start a clean local frontend on another localhost port and set `ACCESS2_E2E_BASE_URL` to that port. The local mutation spec still refuses production/Railway-like hosts.
- Cold local Next.js route compilation can make mutation UI updates slower than the default Playwright assertion window; the local E2E waits for backend state and visible backlog/button posture rather than relying on immediate DOM replacement.

Local mutation test setup is separate from production demo data:

- `backend/scripts/seed_local_v2_rejection_mutation.py` creates or repairs one disposable local synthetic patient marked `access2-local-v2-mutation:reviewer-rejection`.
- The script requires `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` and fails closed when production-like domains such as `access2.salvardata.com`, `api.salvardata.com`, `railway.app`, or `up.railway.app` appear in configured URL/domain/base/origin environment variables.
- Rerunning the script leaves the disposable local scenario ready for another rejection test; after a prior rejection, it creates a new latest `pending_review` snapshot rather than rewriting the rejected terminal snapshot.
- This path is not a Railway seed path, does not modify `access2-railway-demo:*` patients, and must not be used against shared production demo data.
- A separate gated local Playwright mutation spec exists and has passed against localhost with `1 passed`; production mutation E2E was not run.
- The skipped Demo Patient 3 reviewer rejection path remains skipped for production, and Demo Patient 3 remains the production read-only rejected-posture scenario.

## V2 Mutation Validation Reset Strategy

This section is inspection and planning only. It does not authorize production mutation tests, Railway data mutation, override approval implementation, broad workflow mutation, or deployment configuration changes.

### Current mutation validation posture

- Production Railway E2E remains read-only and uses `frontend/e2e/access2-railway-demo.spec.ts`.
- The production E2E suite validates login, Demo Guide, Release Summary, Reviewer Work Queue, four seeded patient postures, patient proof panels, approved audit bundle downloads, and manifest verification.
- The production E2E suite keeps two expected mutation-path skips:
  - Demo Patient 3 reviewer rejection through UI.
  - Demo Patient 4 superuser override approval through UI.
- Local reviewer rejection mutation validation uses `frontend/e2e/access2-local-v2-rejection-mutation.spec.ts` and a disposable synthetic patient created by `backend/scripts/seed_local_v2_rejection_mutation.py`.
- The local mutation seed and local mutation Playwright spec both require explicit opt-in and refuse production/Railway-like targets.

### Existing seed and reset mechanisms

- `backend/scripts/seed_demo_users.py` creates the synthetic demo organization users and is safe to rerun because it skips existing users.
- `backend/scripts/seed_railway_demo_cases.py` creates or repairs four stable synthetic Railway demo patients with `external_patient_id` values starting with `access2-railway-demo:`.
- Railway demo seeding is idempotent for the four read-only demo postures: audit-ready, missing-evidence, rejected-review, and override-approval.
- Railway demo seeding should remain a deliberate one-time operational step and must not be left as the Railway backend startup command.
- `backend/scripts/seed_local_v2_rejection_mutation.py` is separate from Railway demo seeding and uses the marker `access2-local-v2-mutation:reviewer-rejection`.
- The local mutation seed restores a latest `pending_review` snapshot after a prior local rejection by creating a new latest snapshot instead of rewriting a rejected terminal snapshot.

### Existing production safeguards

- `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` is required before local mutation seeding or local mutation E2E can run.
- The local mutation seed refuses configured URL, URI, origin, host, domain, or base environment variables containing `access2.salvardata.com`, `api.salvardata.com`, `railway.app`, or `up.railway.app`.
- The local mutation Playwright spec checks both frontend and API targets and throws when either target looks production-like.
- The shared mutation host guard allows loopback targets by default, blocks missing, malformed, production-like, and unallowlisted non-local targets, and supports explicit future staging host allowlists without enabling staging mutation E2E.
- The local mutation marker is distinct from `access2-railway-demo:*`, and tests assert the local mutation seed does not change Railway demo patients.
- Demo Patient 3 remains intentionally seeded as already rejected, so it is evidence for read-only rejected posture, not a repeatable production rejection target.

### Candidate safe environments

- Local-only disposable database: recommended current target. It already has an opt-in seed, a disposable patient marker, production-target refusal, and a gated Playwright mutation spec.
- Temporary preview environment: acceptable future target only if it has an isolated database, isolated frontend/API URLs, disposable synthetic tenant, seeded credentials, explicit teardown/reset steps, and fail-closed host allow/deny checks.
- Railway staging: acceptable future target only if staging is a separate Railway project or service set with a separate database and no shared demo patients from production.
- Separately seeded disposable tenant in production: not recommended as the next step. It still risks credential, host, and cleanup mistakes unless tenant isolation, reset ownership, and production-safe allowlisting are implemented and reviewed first.
- Shared production demo tenant: not acceptable for mutation validation. It must remain stable for demos and read-only production E2E.

### Minimum requirements before non-local mutation validation

- A disposable synthetic tenant or environment that is not the shared production demo tenant.
- Stable synthetic markers for mutation-only patients, separate from all `access2-railway-demo:*` markers.
- A seed/reset script that can restore the exact pre-test mutation state without rewriting terminal snapshots or deleting unrelated data.
- Explicit environment opt-in, such as a mutation-specific enable flag, plus host checks that fail closed for production and shared Railway demo targets.
- Separate credentials and environment variables for the disposable target; no secrets committed to docs, code, logs, screenshots, or pull requests.
- E2E specs that are separate from production read-only specs and cannot run against production by default.
- A documented teardown/reset command and a post-run verification that the disposable patient returns to a safe pending-review state for the next run.
- Confirmation that tenant scoping, immutable snapshot content, audit events, and persisted manifest verification behavior remain unchanged.

### Reset and reseed requirements

- Reset must create a new latest pending snapshot when the previous disposable snapshot reached a terminal state.
- Reset must not mutate `packet_json` or `packet_markdown` on any existing immutable snapshot.
- Reset must not rewrite rejected, approved, or override-approved terminal review history.
- Reset must not alter shared seeded production patients or their `access2-railway-demo:*` markers.
- Reseed output must print copy/paste-friendly patient IDs or env vars for the mutation spec.
- Reseed must be idempotent and must include tests proving rerun behavior, production-target refusal, and separation from Railway demo cases.

### Explicit non-goals

- No production mutation E2E against `https://access2.salvardata.com`.
- No mutation of shared Railway production demo data.
- No Railway deployment configuration change.
- No backend startup command change; it remains `bash scripts/render-start.sh`.
- No seed command left as a Railway startup command.
- No superuser override approval UI implementation.
- No reviewer directory, role/permission redesign, intervention/task mutation, evidence editing, broad workflow mutation, or architecture redesign.
- No real PHI and no secrets.

### Recommended next implementation

Keep mutation validation local-only until a disposable staging tenant or isolated preview environment exists. The next implementation slice should be a small planning-to-code bridge that generalizes the existing local fail-closed guard pattern into a reusable mutation-target guard for future non-local disposable environments, with tests proving that production and shared Railway demo targets are refused by default.

## Scope for Recommended Slice

The V2 rejection slice should include only the minimum behavior needed for a controlled reviewer rejection.

Backend scope:

- Add or confirm the backend endpoint for rejecting a review packet snapshot if it is missing.
- Keep the route thin and place workflow validation in the service layer.
- Require a non-empty rejection reason.
- Validate snapshot state before rejection.
- Preserve tenant scoping on every read and mutation.
- Preserve patient consistency across the rejected snapshot and linked workflow records.
- Record an audit event for successful rejection only.
- Do not mutate immutable snapshot packet content.
- Ensure rejected state is persisted deterministically and visible through existing read models.

Frontend scope:

- Add the rejection control only where the snapshot is in the correct state for reviewer rejection.
- Require a rejection reason before submitting.
- Show clear disabled or read-only states anywhere rejection is not allowed.
- Do not add approve, override, assignment, create-snapshot, or broad workflow mutation controls as part of this slice.
- Keep the UI tied to existing page structure and stable E2E selectors.

Test scope:

- Add focused backend pytest coverage for rejection service behavior and endpoint behavior.
- Cover rejection reason required.
- Cover tenant scoping.
- Cover immutable snapshot behavior.
- Cover invalid-state rejection attempts.
- Add focused frontend unit or helper tests only if the UI logic introduces meaningful branching.
- Convert the Demo Patient 3 reviewer rejection Playwright path from expected skip to active only after the feature exists and is safe.

## Non-goals

- No real PHI.
- No AI extraction or AI-generated care recommendations.
- No broad workflow builder.
- No generic case-management feature set.
- No uncontrolled frontend mutation controls.
- No override approval until the rejection path is safe.
- No reviewer assignment unless it is strictly required for the rejection path.
- No audit bundle export mutation changes in this slice.
- No Railway deployment configuration changes.
- No backend startup command changes.
- No seed command left as a Railway startup command.
- No broad frontend redesign.
- No architecture redesign or broad backend refactor.

## Validation Strategy

### Backend

- Run focused pytest coverage for the rejection service and endpoint.
- Verify rejection reason is required.
- Verify tenant scoping prevents cross-tenant rejection.
- Verify immutable snapshot packet content is not changed.
- Verify audit events are recorded only on successful rejection.
- Verify invalid snapshot states cannot be rejected.

### Frontend

- Add unit or helper tests if the rejection UI has branch logic worth isolating.
- Add or update Playwright coverage for Demo Patient 3 reviewer rejection through UI.
- Replace the current expected skip only after the feature exists, has backend protection, and has safe frontend state gating.
- Preserve read-only or disabled states on snapshots where rejection is not allowed.

### Production

- Do not run production mutation tests against shared demo data unless a safe reset or reseed strategy is documented.
- Keep the current production baseline of `8 passed, 2 skipped, 0 failed` until the controlled rejection operation is intentionally deployed and production demo data can be safely reset.
- Treat shared demo state as synthetic but still operationally sensitive because mutation tests can alter future demos.
- Demo Patient 3 is already seeded as rejected, so it is not a repeatable production mutation target.
- Keep the Playwright test named `Demo Patient 3 reviewer rejection through UI` skipped until a safe reset or reseed strategy exists.
- Future local mutation E2E should use the disposable local marker `access2-local-v2-mutation:reviewer-rejection`, not Demo Patient 3.
- Future production mutation E2E still requires documented reset/reseed steps before any activation.

## Rollout and Risk Notes

- Start synthetic-only.
- Validate locally first.
- Deploy to Railway only after focused backend, frontend, and E2E tests pass.
- Update the demo data recreation checklist if the rejection action changes demo state or expected reset steps.
- Preserve the V1 read-only demo posture until the controlled operation is intentionally enabled.
- Keep Demo Patient 3 as the production read-only rejected-posture scenario.
- Do not enable override approval in the same slice.
- Do not run production mutation checks without a documented reset path.
- Do not change Railway deployment configuration or the backend startup command for this rollout.

## Proposed Implementation Sequence

1. Inspect existing backend rejection support and tests.
2. Inspect the current skipped Playwright test.
3. Document the rejection contract.
4. Implement the smallest backend and frontend changes.
5. Update E2E from skip to active only when safe.
6. Update docs.

## Follow-up Candidates

- Plan a separate superuser override approval slice after rejection is proven safe.
- Plan a controlled audit bundle export action after review lifecycle mutation is stable.
- Plan outcome/evidence capture improvements as a focused evidence-quality slice.
- Plan reviewer assignment only if reviewer ownership becomes necessary for state gating or audit accountability.
