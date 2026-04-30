# ACCESS2 Agent Guidance

## Required Project Direction

Before making changes, read and follow:

- `docs/access2-v1-scope-control.md`

That document is the ACCESS2 V1 scope guardrail. It defines what belongs in the first version, what must be deferred, and how to prevent scope creep.

If a requested change conflicts with this file or the V1 scope-control document, ask for clarification before changing code.

## Project Purpose

ACCESS2 is an API-first, production-oriented system designed to support the CMS ACCESS model: Advancing Chronic Care with Effective, Scalable Solutions.

The platform goal is to:

- manage chronic care workflows
- track interventions
- measure outcomes
- generate audit-ready evidence for CMS outcome-based payments

The core product requirement is:

> ACCESS2 must prove that care interventions led to measurable outcomes and that escalations were resolved with defensible evidence.

## V1 Product Spine

ACCESS2 V1 must stay focused on this demo path:

**login → patient/worklist → intervention/outcome evidence → review packet → approval → audit bundle export → verification**

All development work should support this path.

If a proposed feature does not support this path, document it as follow-up only unless explicitly instructed otherwise.

## Current Project Priority

Current priority is completing the first usable version of ACCESS2.

The priority is not broad UI polish, AI features, analytics, billing, integrations, or full healthcare platform functionality.

The priority is making the ACCESS2 evidence and audit workflow usable end-to-end.

## Core Workflow Chain

The evidence chain is:

**signal → escalation → intervention → outcome → care update → resolution → evidence → case summary → immutable review packet → approval → audit bundle**

Future work should strengthen this chain rather than expand the product sideways.

## What Matters Most

The system must be able to prove:

- why a patient required action
- what intervention occurred
- what measurable outcome followed
- how the escalation or care gap was resolved
- what evidence supports closure
- who reviewed and approved the evidence
- what audit bundle was exported
- whether the audit bundle can be verified against persisted data

This means future work should prioritize:

- auditable workflow state transitions
- deterministic linkage between workflow objects
- patient-safe and tenant-safe relationships
- immutable review evidence
- evidence summaries that support review, audit, and payment justification
- closure/resolution evidence, not just event capture

## Scope Control

Stay within ACCESS2 V1 scope.

Do not add these unless explicitly requested as a separate post-V1 slice:

- AI recommendations
- AI-generated care plans
- predictive analytics
- broad analytics dashboards unrelated to audit readiness
- billing workflows
- payment reconciliation
- EHR integration
- FHIR integration
- real CMS submission integration
- patient portal
- provider messaging
- mobile app
- complex role-based permission system
- multi-organization admin console
- broad frontend redesign
- broad backend refactors
- generic case-management features

If something useful is discovered outside the current slice, document it in the follow-up section only. Do not silently build it.

## Architecture Rules

- Keep the existing architecture.
- Do not redesign the system.
- Keep business logic in services.
- Keep API routes thin.
- Build on current repo patterns.
- Prefer small, production-minded slices.
- Avoid unnecessary abstractions.
- Avoid unrelated cleanup.
- Do not introduce generic case-management features unless explicitly requested.
- Do frontend/UI work only when the requested slice explicitly calls for it.
- Treat migrations and tests as part of the feature, not follow-up work.

## ACCESS2 Invariants

Preserve these at all times:

- Snapshots are immutable once created.
- Read-only endpoints do not mutate data.
- Audit bundle exports log events only on successful export.
- Tenant scoping is preserved.
- Patient consistency is preserved across linked records.
- Backend business logic stays in services.
- API routes stay thin.
- Tests remain deterministic.
- Timeline and evidence views use deterministic ordering.
- Persisted `packet_json` and `packet_markdown` are not rebuilt during audit reads.
- Audit bundle verification compares supplied manifests against persisted snapshot data.

## Backend Priority Order

When choosing or shaping the next backend slice, prefer work that strengthens one or more of these:

1. causal traceability across the workflow chain
2. auditable evidence generation
3. deterministic workflow linkage
4. escalation resolution and closure evidence
5. review-packet immutability
6. audit-bundle export and verification
7. targeted verification and regression protection

Prefer slices that make the system more defensible in a CMS ACCESS-style review.

## Frontend Priority Order

When frontend work is explicitly requested, prefer work that supports the V1 demo path:

1. audit-readiness dashboard
2. review queue visibility
3. patient audit status
4. patient evidence chain
5. review packet visibility
6. controlled snapshot actions
7. audit bundle export and verification
8. beginner-friendly demo flow

Avoid frontend polish that does not help complete the V1 demo path.

## Implementation Preferences

- Reuse existing models, schemas, services, and router patterns.
- Prefer explicit validation in services over implicit ORM behavior.
- Keep tenant scoping strict.
- Keep patient consistency strict across linked records.
- Preserve deterministic ordering in timeline and evidence views.
- Keep changes narrow and auditable.
- Prefer clear names over clever abstractions.
- Use existing endpoint, schema, and service naming conventions.
- Do not mutate immutable packet or snapshot content during read paths.
- Avoid adding new tables or migrations unless the slice truly requires it.

## Development Slice Rules

Each development slice should be small and testable.

Prefer:

- 1 to 4 files changed
- one backend endpoint or one frontend page/section at a time
- narrow service-level logic
- focused tests
- clear implementation summary
- clear follow-up list

Avoid:

- architecture redesign
- broad refactoring
- multiple unrelated features
- “while I’m here” cleanup
- new abstractions unless clearly needed
- UI redesigns
- expanding scope while implementing the requested task

If unexpected backend files, frontend app files, tests, generated artifacts, or unrelated files appear required for a slice, stop and report instead of expanding scope.

## Testing Expectations

For backend slices:

- add focused pytest coverage
- run targeted regression tests for affected workflow areas
- verify Alembic upgrade head succeeds when migrations are involved
- prefer stable, narrowly scoped tests for timeline, evidence, review-packet, and audit behavior

For frontend slices:

- run relevant frontend tests
- run lint
- run build or typecheck when appropriate
- update Selenium smoke coverage only for critical user-visible paths

Do not claim a slice is complete unless relevant tests were run or skipped with a clear reason.

## Practical Repo Notes

- Repo root: `C:\dev\access2`
- Backend directory: `C:\dev\access2\backend`
- Frontend directory: `C:\dev\access2\frontend`
- Alembic should be run from `C:\dev\access2\backend`
- From the backend directory, use test paths like `tests/...`
- From repo root, use test paths like `backend/tests/...`
- PowerShell is the preferred command shell for local instructions

## Definition of Done

A task is done only when:

- the requested behavior works
- relevant tests pass
- no unrelated files are changed
- existing behavior is preserved
- ACCESS2 invariants are preserved
- docs/manual steps are updated when relevant
- the change can be summarized in 3 to 5 bullets
- follow-up work is documented but not silently built

## Default Response Format for Completed Coding Slices

When reporting completion, include:

1. Findings
2. Implementation Summary
3. Files Changed
4. Tests Run
5. Follow-Up

Keep the summary concise, factual, and focused on what changed.
