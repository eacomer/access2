# ACCESS2 Backend Agent Guidance

## Backend Mission

The ACCESS2 backend is the core workflow and evidence engine for the CMS ACCESS model.

The backend must support this chain:

**signal → escalation → intervention → outcome → care update → evidence**

The highest priority is not broad feature expansion. The highest priority is ensuring the backend can prove:

- what triggered action
- what intervention occurred
- what outcome was measured
- what care update was recorded
- what evidence supports the result
- whether and why an escalation was resolved or remains open

## Non-Negotiable Rules

- Keep business logic in services.
- Keep API routes thin.
- Do not redesign the architecture.
- Do not add unnecessary abstractions.
- Prefer small, production-minded slices.
- Reuse current repo patterns for models, schemas, services, routers, and tests.
- Favor explicit validation and deterministic behavior.

## Data Integrity Rules

All new backend work must preserve:

- strict tenant scoping
- strict same-patient validation across linked workflow objects
- deterministic linkage between signals, escalations, tasks, outcomes, care updates, and evidence
- deterministic ordering in timeline and evidence outputs
- auditability of status changes and closure decisions

When linking records across entities, validate in the service layer rather than relying on assumptions.

## Slice Selection Guidance

Prefer backend slices that improve:

1. auditable workflow progression
2. closure/resolution evidence
3. deterministic evidence summaries
4. timeline fidelity
5. targeted regression coverage

Avoid backend work that primarily adds polish without strengthening evidence, traceability, or auditability.

## Service-Layer Guidance

When adding or changing service logic:

- validate org scope
- validate patient consistency
- validate cross-object linkage explicitly
- reject invalid cross-tenant or cross-patient references
- keep write paths deterministic
- keep read ordering deterministic
- keep derived evidence summaries explainable and stable

## API Guidance

- Keep endpoints thin.
- Put business rules in services.
- Follow existing route and schema patterns.
- Do not expand scope into generic notes, messaging, or case management unless explicitly requested.
- Prefer narrowly scoped workflow actions over broad multi-purpose endpoints.

## Migration Guidance

- Follow existing Alembic patterns already used in this repo.
- Keep migrations minimal and reversible.
- Verify `upgrade head` succeeds as part of the slice.
- Be careful with enum handling and repo-specific migration patterns.

## Testing Guidance

Every backend slice should include:

- focused pytest coverage for the new behavior
- targeted regression coverage for adjacent workflow behavior
- timeline coverage if timeline output changes
- evidence/report coverage if evidence output changes

Prefer stable, explicitly named tests that are easy to target in future runs.

## Practical Execution Notes

- Run Alembic from: `C:\dev\access2\backend`
- From that directory, use test paths like:
  - `tests/test_patient_timeline.py`
  - `tests/test_outcomes.py`
  - `tests/test_care_updates.py`
- If running from repo root, use `backend/tests/...` paths instead.

## Current Backend Track

The backend has already established:

- outcome capture
- ACCESS evidence reporting
- care update capture
- timeline integration for these workflow objects

The next preferred backend direction is:

**escalation resolution / closure evidence**

Keep future changes aligned to that track unless explicitly told otherwise.