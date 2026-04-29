# ACCESS2 Agent Guidance

## Project Direction

ACCESS2 is an API-first, production-oriented system designed to support the CMS ACCESS model (Advancing Chronic Care with Effective, Scalable Solutions).

The platform goal is to:

- manage chronic care workflows
- track interventions
- measure outcomes
- generate audit-ready evidence for CMS outcome-based payments

Current project priority is not UI polish. Current priority is building a backend evidence engine that can prove that care interventions led to measurable outcomes and defensible workflow closure.

The core workflow chain is:

**signal → escalation → intervention → outcome → care update → evidence**

## What matters most

The most important product requirement is:

**The system must be able to prove that interventions led to measurable outcomes, and that escalations were resolved with defensible evidence.**

That means future work should prioritize:

- auditable workflow state transitions
- deterministic linkage between workflow objects
- patient-safe and tenant-safe relationships
- evidence summaries that can support review, audit, and payment justification
- closure/resolution evidence, not just event capture

## Architecture Rules

- Keep the existing architecture.
- Do not redesign the system.
- Keep business logic in services.
- Keep API routes thin.
- Prefer small, production-minded slices.
- Build on current repo patterns.
- Avoid unnecessary abstractions.
- Do not introduce generic case-management features unless explicitly requested.
- Do not do frontend/UI work unless explicitly requested.

## Backend Priority Order

When choosing the next slice, prefer work that strengthens one or more of these:

1. causal traceability across the workflow chain
2. auditable evidence generation
3. deterministic workflow linkage
4. escalation resolution / closure evidence
5. targeted verification and regression protection

Prefer slices that make the system more defensible in a CMS ACCESS-style review.

## Implementation Preferences

- Reuse existing models, schemas, services, and router patterns.
- Prefer explicit validation in services over implicit ORM behavior.
- Keep tenant scoping strict.
- Keep patient consistency strict across linked records.
- Preserve deterministic ordering in timeline and evidence views.
- Treat migrations and tests as part of the feature, not as follow-up work.

## Testing Expectations

For backend slices:

- add focused pytest coverage
- run targeted regression tests for affected workflow areas
- verify Alembic upgrade head succeeds
- prefer stable, narrowly scoped tests for timeline/evidence behavior

## Practical Repo Notes

- Alembic should be run from `C:\dev\access2\backend`
- From the backend directory, use test paths like `tests/...`
- From repo root, use test paths like `backend/tests/...`

Keep changes incremental, auditable, and easy to validate.