# ACCESS2 V2 Product Workflow Next Slice Decision

## Purpose

This document selects the next non-staging ACCESS2 V2 product workflow slice. It pauses staging work unless isolated staging infrastructure is actually available, and it keeps the next step focused on product and demo clarity rather than new mutation behavior.

This is a docs-only decision point. It does not authorize product behavior changes, staging implementation, staging mutation E2E, production mutation E2E, Railway configuration changes, backend startup changes, secrets, or production demo-data mutation.

## Current Product Status

- The local V2 correction loop is proven on localhost only.
- The local proof covers assignment, rejection with reason, corrected evidence, a new immutable pending snapshot, corrected packet approval, preserved old immutable rejected packet history, and terminal read-only approved posture.
- The V2 correction-loop demo script is polished and operator-ready.
- Patient detail now explains latest actionable packet, historical approved/rejected packets, corrected snapshots, and local-only/read-only posture.
- Reviewer Work Queue now explains immutable snapshot review posture and remains read-only.
- Patient detail now explains that audit bundles export snapshot evidence and manifests verify exported artifacts.
- Production remains V1 read-only and synthetic/demo-only.
- The staging path is documented through readiness, environment template, seed/reset contract, dry-run guard, host guard behavior, decision point, isolated staging plan, and provisioning checklist, but staging is not implemented.
- The next work should either consolidate demo readiness, continue small read-only product clarity, or return to staging only if isolated staging is provisioned and approved.

## Product Clarity Completion Checkpoint

Completed product clarity slices:

- `Polish V2 correction loop demo script`
- `Add patient correction loop status messaging`
- `Clarify reviewer immutable snapshot UX`
- `Polish audit bundle manifest visibility`

What improved:

- Operators can explain the localhost correction loop in a 5-10 minute script.
- Operators can distinguish the latest actionable `pending_review` packet from historical approved/rejected packets.
- Patient detail and Reviewer Work Queue now state that immutable `packet_json` and `packet_markdown` are not refreshed or overwritten.
- Corrected evidence is framed as creating a new immutable snapshot, not changing the old rejected packet.
- Audit bundles are framed as read-only exports of persisted snapshot evidence.
- Manifest verification is framed as proof that exported artifacts match persisted snapshot data, not as a review decision control.
- Reviewer Work Queue and production V1 read-only posture remain explicit.

What did not change:

- No backend behavior changed.
- No frontend mutation behavior changed.
- No E2E mutation behavior changed.
- No new routes or mutation controls were added.
- No staging implementation was added.
- No production mutation testing was run.
- No Railway configuration changed.
- No superuser override approval or broad workflow mutation controls were added.

Validation summary:

- Patient correction-loop status messaging: `npm test` 73 passed, lint passed, typecheck passed.
- Reviewer immutable snapshot UX: `npm test` 75 passed, lint passed, typecheck passed.
- Audit bundle/manifest visibility: `npm test` 76 passed, lint passed, typecheck passed.
- `git diff --check` passed for each slice with only normal CRLF warnings.
- Local mutation E2E was skipped in recent copy-only slices when safe localhost env/listeners were unavailable.
- Staging and production mutation tests were intentionally skipped.

## Candidate Comparison

| Candidate | Value | Risk | Size | Change surface | Decision |
| --- | --- | --- | --- | --- | --- |
| A. V2 correction-loop demo script polish | High. Improves operator storytelling for the completed local proof chain. | Very low. Docs-only and does not change behavior. | Small. | Docs only. | Recommend first. |
| B. Patient-detail correction-loop status messaging | High. Helps operators understand latest actionable packet, historical rejected packet, corrected pending or approved packet, and immutable snapshots. | Low to moderate. Frontend copy must not imply new mutation permissions. | Small frontend slice with focused tests if implemented later. | Frontend, docs, possibly targeted E2E updates. | Recommend second after the demo script. |
| C. Audit bundle/manifest visibility polish | Medium to high. Aligns directly with audit bundle and manifest verification proof. | Low to moderate. Must stay read-only and avoid changing export semantics. | Small to medium depending on UI surface. | Frontend, docs, possibly targeted E2E updates. | Consider after A and B. |
| D. Reviewer UX copy around immutable snapshots | Medium. Clarifies terminal read-only posture and why Reviewer Work Queue remains read-only. | Low. Copy-only if scoped carefully. | Small. | Frontend and docs if implemented later. | Could pair with B, but not first. |
| E. Superuser override approval | Potentially useful later for exceptions, but not needed for the current proof chain. | High. Requires permission, governance, audit wording, and staging validation. | Large. | Backend, frontend, E2E, docs, permissions. | Explicitly defer. |
| F. Broad workflow mutation controls | Unclear value for the next narrow V2 slice. | High. Risks scope creep and premature mutation surface expansion. | Broad. | Backend, frontend, E2E, docs. | Explicitly reject for now. |

## Current Recommended Next Options

- Option A: Continue product clarity.
  Candidate slices include small read-only demo/release summary polish, improved operator navigation between patient detail, Reviewer Work Queue, and the demo script, or a non-mutating audit proof checklist in UI/docs.
- Option B: Return to staging.
  Choose this only if isolated staging infrastructure is ready. Use [access2-v2-staging-provisioning-checklist.md](C:/dev/access2/docs/access2-v2-staging-provisioning-checklist.md) first.
- Option C: Begin a carefully scoped next local-only product behavior.
  Choose this only if it fits the existing correction-loop guardrails. Do not choose superuser override approval yet.

## Recommended Next Slice

Recommend: `Document V2 demo readiness handoff`.

Rationale:

- It is the lowest-risk next slice after the completed product clarity polish.
- It is docs-only and does not add mutation behavior.
- It consolidates the completed local V2 proof and product clarity story.
- It gives operators a clean handoff before either staging work or more UI work.
- It keeps production read-only and avoids broad workflow mutation controls.

## Secondary Recommendation

If the demo readiness handoff is already accepted, continue with a small read-only product clarity slice only if it improves the ACCESS proof chain. Otherwise, return to staging only after isolated staging infrastructure exists and the provisioning checklist is complete.

## Explicitly Deferred

- Superuser override approval.
- Broad workflow mutation controls.
- Staging mutation E2E.
- Production mutation E2E.
- Production demo data mutation.
- Any production or shared Railway demo mutation.

## Definition Of Done For Recommended Next Slice

For `Document V2 demo readiness handoff`, done means:

- The handoff consolidates the completed local correction-loop proof and product clarity polish.
- The handoff identifies the demo script, patient-detail clarity copy, Reviewer Work Queue read-only copy, and audit bundle/manifest proof copy.
- The handoff states production read-only guardrails and production do nots.
- The handoff distinguishes localhost-only V2 mutation proof from production V1 read-only posture.
- The handoff contains no secrets, no real PHI, and no production mutation guidance.

## Suggested Next Prompt

`Document V2 demo readiness handoff`

## Non-Goals

- No product behavior implementation in this decision slice.
- No backend, frontend, or E2E code changes.
- No mutation controls.
- No staging implementation.
- No staging seed/reset implementation.
- No staging mutation E2E.
- No production mutation E2E.
- No production demo data mutation.
- No Railway configuration changes.
- No backend startup command changes.
- No secrets or real PHI.
