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
latest rejected snapshot -> corrected synthetic outcome/evidence -> create new immutable review packet snapshot -> new latest pending_review snapshot -> old rejected packet preserved/read-only
```

The local proof strengthens the core ACCESS2 product requirement: interventions must connect to measurable outcomes and defensible evidence. A rejected packet is not refreshed or edited. Corrected current evidence is captured by creating a new immutable review packet snapshot while historical rejected/approved packets remain available as audit evidence.

## What V2 Proves Today

- A reviewer can reject the latest `pending_review` packet with a required reason in a controlled local flow.
- A reviewer can be assigned to the latest `pending_review` packet in a controlled local flow.
- A new immutable review packet snapshot can be created from current evidence after rejection.
- Old `packet_json` and `packet_markdown` remain preserved for rejected, approved, and historical packets.
- Local seed/reset can create a visible synthetic correction story using a later `systolic_bp` outcome and post-rejection care update.
- Local mutation E2E validates the chain from assignment to rejection to corrected evidence to new pending snapshot.
- Reviewer Work Queue remains read-only; mutation controls stay patient-detail-only.
- Local mutation E2E is gated by `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` and refuses production/Railway-like hosts.

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
- V2 correction-loop E2E: local-only flow validates assignment, rejection, corrected evidence, new pending snapshot, preserved old rejected packet, and read-only queue posture.
- Local seed proof story: disposable synthetic marker creates or repairs a local scenario with post-rejection correction evidence.
- Demo/runbook docs: local-only correction-loop script, troubleshooting, and production don’ts are documented.

## What Remains Before Production-Grade V2

- Production-grade mutation governance: define who may assign, reject, approve, and create snapshots in a real deployment posture.
- Isolated staging or preview environment: separate frontend/API/database/tenant from shared production demo data.
- Reset/reseed strategy outside localhost: deterministic disposable targets, pre-test state restoration, post-test verification, and teardown guidance.
- Stronger audit-role permissions if needed: keep this narrow and avoid a broad role-management redesign.
- Controlled approval of a corrected pending packet, local-only first.
- A production-safe promotion plan that keeps V1 production read-only until mutation governance and disposable validation are proven.
- Documentation alignment so local V2 guidance does not drift from production V1 read-only guardrails.

## Highest Current Risks

- Accidentally mutating shared production demo data.
- Confusing creation of a new immutable snapshot with refreshing or editing an old packet.
- Adding approval or override behavior before rejection/correction governance is production-safe.
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

## Recommended Next Implementation Candidate

The next smallest implementation candidate is controlled approval of the newly corrected pending packet, local-only first.

Recommended boundaries:

- Use the disposable local mutation scenario only.
- Expose approval only on patient detail.
- Allow approval only for the latest `pending_review` snapshot.
- Preserve rejected/approved/historical packet immutability.
- Keep Reviewer Work Queue read-only.
- Keep production E2E read-only and production mutation tests skipped.
- Require local seed/reset and gated local E2E validation.
- Record audit events only on successful approval.
- Keep backend validation in services and routes thin.

This should wait until the checkpoint is accepted because approval can move a case toward audit-bundle readiness. It is higher risk than rejection or assignment and should not be combined with override approval.

## Why Override Approval Should Still Wait

Override approval can approve a packet despite readiness gaps. That is useful for exception handling, but it is also the riskiest review mutation because it can create an audit-ready or exportable posture from incomplete evidence. ACCESS2 should first prove normal approval of a corrected pending packet in a disposable local environment, then decide whether override approval needs separate governance, permissions, audit wording, and validation.

## Reference Documents

- [access2-v2-planning.md](C:/dev/access2/docs/access2-v2-planning.md)
- [access2-v2-correction-loop-demo.md](C:/dev/access2/docs/access2-v2-correction-loop-demo.md)
- [access2-demo-data-recreation-checklist.md](C:/dev/access2/docs/access2-demo-data-recreation-checklist.md)
- [access2-v1-demo-handoff-summary.md](C:/dev/access2/docs/access2-v1-demo-handoff-summary.md)
- [access2-v1-scope-control.md](C:/dev/access2/docs/access2-v1-scope-control.md)
