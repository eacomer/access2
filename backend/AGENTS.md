# backend/AGENTS.md

## Backend scope

This file governs backend implementation work for access2.

access2 is a production-oriented healthcare SaaS application under active development.  
The backend is being built as a **modular monolith**, with clear service-layer boundaries and portable infrastructure assumptions.

This is **not** a demo backend. Build each slice as if it may become part of a real provider-facing SaaS platform.

The product direction is now centered on **ACCESS-aligned care operations and outcomes evidence workflows**, not generic CRUD.

---

## Current product target

The current build target is:

**Patient → Enrollment/Consent → Signal → Escalation → Care Update → Outcome Evidence**

Prefer backend work that directly supports:
- patient records within an organization
- enrollment and consent workflows
- clinical track assignment
- signal capture and evaluation
- escalation and intervention workflows
- clinician-facing care updates
- outcomes evidence
- auditability and reporting readiness

Avoid drifting into generic admin features unless they are required to unblock these workflow slices.

---

## Backend architecture rules

### 1) Inspect the real code first
Before changing anything:
- inspect the real repo structure
- inspect existing models, schemas, services, routes, and migrations
- reuse current patterns where they already exist

Do not assume earlier examples still match the codebase.

### 2) Keep the backend modular
Preserve clear boundaries between:
- `app/api` → HTTP and dependency layer
- `app/services` → business logic
- `app/models` → persistence models
- `app/schemas` → request/response schemas
- `app/core` → config, security, database, request context, shared infrastructure

### 3) Keep routes thin
FastAPI route handlers should mainly:
- validate input
- resolve dependencies
- call service-layer methods
- translate expected failures into HTTP responses

Do not place core business rules in route functions.

### 4) Keep business logic in services
Put workflow behavior in `app/services`.

This includes:
- enrollment rules
- consent validation
- signal evaluation
- threshold checks
- escalation decisions
- care update generation
- outcome/evidence calculations
- tenant scoping checks

### 5) Prefer deterministic rules
For healthcare workflow behavior, prefer deterministic, explainable, and testable rules.

Examples:
- signal thresholds
- escalation triggers
- state transitions
- evidence calculations
- reporting eligibility rules

Do not hide core operational logic in vague helpers or premature AI layers.

### 6) Keep AI separate from deterministic workflow logic
If future AI-assisted features are added, they must remain clearly separated from:
- access control
- workflow state transitions
- evidence generation
- reporting logic
- threshold decisions

AI can assist; it should not silently replace core deterministic application behavior unless explicitly designed and approved.

---

## ACCESS-aligned implementation guidance

Backend work should increasingly support an ACCESS-style care operations platform.

When building new slices, think in terms of:
- organization
- patient
- care track
- enrollment
- consent
- signal
- escalation
- care milestone
- care update
- outcome evidence
- reporting event

Do not reduce everything to generic table CRUD if the real workflow implies state transitions or operational meaning.

Prefer domain shapes that can later support:
- track-specific workflows
- patient-reported and clinical measures
- clinician coordination
- audit history
- future CMS/FHIR-style reporting/export adapters

---

## Multi-tenant and authorization rules

access2 is a provider-facing SaaS.  
Most backend slices should be organization-aware.

When existing tenant-aware patterns are present:
- reuse `RequestContext`
- reuse centralized authorization helpers
- keep organization scoping out of route handlers when possible
- enforce tenant boundaries in services and/or shared authz helpers
- keep superuser/global access explicit and intentional

### Tenant-aware design expectations
For tenant-scoped resources:
- include `organization_id` where appropriate
- use explicit foreign keys
- use explicit uniqueness constraints scoped correctly for multi-tenant behavior
- avoid accidental cross-tenant reads or writes

### Authorization expectations
- Non-superusers should be scoped to their organization unless the slice explicitly requires otherwise.
- Superuser/global behavior should be deliberate, not accidental.
- Do not duplicate authorization logic across routes if a shared helper or service rule can centralize it.

Do not introduce a heavyweight tenancy or RBAC framework unless explicitly requested.

---

## Data model and migration rules

### 1) Migrations are required for persistent model changes
If a model change affects persistence, include an Alembic migration when appropriate.

### 2) Keep models explicit
Prefer explicit columns, relationships, and constraints.
Do not rely on implicit behavior where clarity matters.

### 3) Reuse established patterns
Reuse the project’s existing patterns for:
- base model inheritance
- UUID primary keys
- timestamps
- naming conventions
- active/inactive flags

### 4) Model for workflow traceability
Where relevant, design models to preserve:
- state
- timestamps
- actor/user references
- organization context
- evidence provenance

Do not overbuild a full audit framework unless requested, but do not design in a way that destroys traceability.

### 5) Keep migrations straightforward
Prefer migrations that are:
- readable
- minimal
- reversible when practical

Avoid unnecessary migration complexity.

---

## API design rules

- Reuse `/api/v1` routing patterns.
- Keep request and response schemas explicit.
- Keep update surfaces narrow.
- Prefer intentional workflow endpoints when needed instead of exposing only raw CRUD.
- Return clear status codes and actionable error messages.
- Keep security boundaries obvious in route dependencies.

Examples of acceptable workflow-oriented endpoints:
- enroll patient
- record consent
- submit signal
- acknowledge escalation
- resolve escalation
- generate care update

Do not force every workflow into generic PATCH semantics if a clearer domain action exists.

---

## Service-layer rules

Service methods should:
- enforce domain rules
- enforce tenant boundaries where appropriate
- return clear business outcomes
- raise predictable errors for expected failure conditions
- remain easy to unit test

Avoid:
- hidden side effects
- large god services
- cross-layer leakage of HTTP concerns into service code

Prefer small, focused services or service functions grouped by domain area.

---

## Schema rules

Use Pydantic schemas to make the API explicit.

Prefer:
- create/update/read schemas
- narrow admin-only update surfaces
- typed enums where they improve workflow clarity
- explicit validation for fields that matter operationally

Do not use overly permissive catch-all payloads for important healthcare workflow objects.

---

## Testing expectations

For backend changes, add or update focused pytest coverage.

Prefer:
- endpoint tests for route behavior
- service tests for domain behavior
- regression tests for authz and tenant scoping
- tests for deterministic workflow transitions
- tests for escalation/evidence rules
- minimal mocking where possible

Each meaningful backend slice should prove:
- happy path
- key denial/error path
- tenant boundary behavior when relevant
- workflow state behavior when relevant

Run the smallest relevant test set first, then expand as needed.

Typical commands:

```powershell
cd C:\dev\access2\backend
py -3 -m pytest tests/test_users.py -v
py -3 -m pytest