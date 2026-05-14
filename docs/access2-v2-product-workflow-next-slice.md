# ACCESS2 V2 Product Workflow Next Slice Decision

## Purpose

This document selects the next non-staging ACCESS2 V2 product workflow slice. It pauses staging work unless isolated staging infrastructure is actually available, and it keeps the next step focused on product and demo clarity rather than new mutation behavior.

This is a docs-only decision point. It does not authorize product behavior changes, staging implementation, staging mutation E2E, production mutation E2E, Railway configuration changes, backend startup changes, secrets, or production demo-data mutation.

## Current Product Status

- The local V2 correction loop is proven on localhost only.
- The local proof covers assignment, rejection with reason, corrected evidence, a new immutable pending snapshot, corrected packet approval, preserved old immutable rejected packet history, and terminal read-only approved posture.
- Production remains V1 read-only and synthetic/demo-only.
- The staging path is documented through readiness, environment template, seed/reset contract, dry-run guard, host guard behavior, decision point, isolated staging plan, and provisioning checklist, but staging is not implemented.
- The next work should be product/demo clarity unless isolated staging is provisioned and approved.

## Candidate Comparison

| Candidate | Value | Risk | Size | Change surface | Decision |
| --- | --- | --- | --- | --- | --- |
| A. V2 correction-loop demo script polish | High. Improves operator storytelling for the completed local proof chain. | Very low. Docs-only and does not change behavior. | Small. | Docs only. | Recommend first. |
| B. Patient-detail correction-loop status messaging | High. Helps operators understand latest actionable packet, historical rejected packet, corrected pending or approved packet, and immutable snapshots. | Low to moderate. Frontend copy must not imply new mutation permissions. | Small frontend slice with focused tests if implemented later. | Frontend, docs, possibly targeted E2E updates. | Recommend second after the demo script. |
| C. Audit bundle/manifest visibility polish | Medium to high. Aligns directly with audit bundle and manifest verification proof. | Low to moderate. Must stay read-only and avoid changing export semantics. | Small to medium depending on UI surface. | Frontend, docs, possibly targeted E2E updates. | Consider after A and B. |
| D. Reviewer UX copy around immutable snapshots | Medium. Clarifies terminal read-only posture and why Reviewer Work Queue remains read-only. | Low. Copy-only if scoped carefully. | Small. | Frontend and docs if implemented later. | Could pair with B, but not first. |
| E. Superuser override approval | Potentially useful later for exceptions, but not needed for the current proof chain. | High. Requires permission, governance, audit wording, and staging validation. | Large. | Backend, frontend, E2E, docs, permissions. | Explicitly defer. |
| F. Broad workflow mutation controls | Unclear value for the next narrow V2 slice. | High. Risks scope creep and premature mutation surface expansion. | Broad. | Backend, frontend, E2E, docs. | Explicitly reject for now. |

## Recommended Next Slice

Recommend Candidate A: V2 correction-loop demo script polish.

Rationale:

- It is the lowest-risk next slice.
- It is docs-only.
- It improves demo readiness without adding mutation behavior.
- It captures the completed local V2 proof while the implementation details are fresh.
- It gives operators a clean 5-10 minute story before any UI polish or staging work.
- It keeps production read-only and avoids broad workflow mutation controls.

## Secondary Recommendation

Candidate B can follow after the demo script: patient-detail correction-loop status messaging.

That later slice should stay read-only in copy and posture unless separately approved. It should explain the latest actionable packet, historical rejected packet, corrected pending or approved packet, and immutable snapshot history without adding new workflow controls.

## Explicitly Deferred

- Superuser override approval.
- Broad workflow mutation controls.
- Staging mutation E2E.
- Production mutation E2E.
- Production demo data mutation.
- Any production or shared Railway demo mutation.

## Definition Of Done For Candidate A

For V2 correction-loop demo script polish, done means:

- An operator can explain the local correction loop in 5-10 minutes.
- The script identifies prerequisites.
- The script identifies the seed/reset command.
- The script identifies the local E2E command.
- The script explains expected UI observations.
- The script explains the audit/evidence talk track.
- The script states production do nots.
- The script contains no secrets and no real PHI.

## Suggested Next Prompt

`Polish V2 correction-loop demo script`

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
