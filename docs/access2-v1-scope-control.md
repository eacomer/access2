# ACCESS2 V1 Scope Control

## Purpose

This document keeps ACCESS2 development focused on the first usable version of the product.

ACCESS2 is not trying to become a full healthcare platform in V1. The first version must prove the core value proposition:

> Track chronic care interventions, connect them to measurable outcomes, and generate audit-ready evidence for CMS ACCESS-style outcome-based payment workflows.

## V1 Product Spine

All V1 work should support this path:

login → patient/worklist → intervention/outcome evidence → review packet → approval → audit bundle export → verification

If a proposed feature does not support this path, defer it.

## V1 In Scope

- Patient list and patient detail
- Worklist / audit-readiness dashboard
- Patient evidence timeline
- Intervention, outcome, care update, and resolution evidence visibility
- ACCESS case summary visibility
- Immutable review packet snapshots
- Reviewer queue
- Snapshot assignment
- Snapshot approve / reject
- Audit bundle export
- Audit bundle verification
- Manual test script
- Automated regression tests
- Demo seed data
- Local runbook
- Optional deployment runbook

## V1 Out of Scope

Do not add these unless explicitly approved as a separate post-V1 slice:

- AI recommendations
- AI-generated care plans
- Predictive analytics
- Advanced analytics dashboards
- Billing workflows
- Payment reconciliation
- EHR integration
- FHIR integration
- Real CMS submission integration
- Patient portal
- Provider messaging
- Mobile app
- Complex role-based permission system
- Multi-organization admin console
- Large frontend redesign
- Broad backend refactors
- UI polish unrelated to completing the demo path

## Scope Gate

Before starting any task, ask:

> Does this help complete the V1 ACCESS2 demo path?

If no, document it as a follow-up and do not build it.

Use this decision rule:

- Supports evidence chain: consider
- Supports V1 demo path: consider
- Reduces audit risk: consider
- Fixes a blocker: do it
- Nice-to-have UI polish: defer
- AI / advanced analytics / integrations: defer

## Development Rules

Each development slice should be small and testable.

Prefer:

- 1 to 4 files changed
- One backend endpoint or one frontend page/section at a time
- Narrow service-level logic
- Thin API routes
- Deterministic tests
- Clear definition of done

Avoid:

- Architecture redesign
- Broad refactoring
- Multiple unrelated features
- “While I’m here” cleanup
- New abstractions unless clearly needed
- UI redesigns
- Frontend mutation controls unless explicitly requested for the current slice

If unexpected backend files, product-code files, generated artifacts, or unrelated files appear necessary for a slice, stop and report instead of expanding scope.

## ACCESS2 Invariants

Preserve these at all times:

- Snapshots are immutable once created.
- Read-only endpoints do not mutate data.
- Audit bundle exports log events only on successful export.
- Tenant scoping is preserved.
- Backend business logic stays in services.
- API routes stay thin.
- Tests must be deterministic.
- Packet JSON and packet Markdown are persisted and not rebuilt during audit reads.
- Audit bundle verification compares supplied manifests against persisted snapshot data.

## Definition of Done for Each Slice

A slice is done only when:

- Intended behavior works.
- Relevant tests pass.
- No unrelated files are changed.
- Existing behavior is preserved.
- Docs/manual steps are updated when relevant.
- The change can be summarized in 3 to 5 bullets.
- Follow-up work is documented but not silently built.

## V1 Completion Definition

ACCESS2 V1 is complete when a user can:

1. Log in.
2. View the audit-readiness dashboard.
3. Open a patient.
4. Understand why the patient is or is not audit-ready.
5. View the patient evidence chain.
6. View or create an immutable review packet snapshot.
7. Assign or review the snapshot.
8. Approve or reject the snapshot.
9. Export an approved audit bundle.
10. Verify the audit bundle.
11. Follow a beginner-friendly manual test script.
12. Run the app locally from documented steps.

## Recommended Remaining V1 Order

1. Org audit-readiness dashboard
2. Review queue UI
3. Controlled snapshot actions
4. Export and verification UI
5. Patient evidence story
6. Demo seed data
7. Manual test script
8. Local runbook
9. Test hardening
10. Optional deployment runbook

## Default Instruction for Future Codex Prompts

Use this instruction in every future development prompt:

```text
Stay within ACCESS2 V1 scope. Do not expand the product scope. Do not add features outside this slice. Do not refactor unrelated code. Do not redesign the architecture. If you notice something outside the slice, document it as follow-up only.

Preserve ACCESS2 invariants:
- snapshots are immutable
- read-only endpoints do not mutate data
- audit bundle exports log events only on successful export
- tenant scoping is preserved
- backend business logic stays in services
- routes stay thin
- tests remain deterministic
- persisted packet_json and packet_markdown are not rebuilt during audit reads
- audit bundle verification compares supplied manifests against persisted snapshot data
```
