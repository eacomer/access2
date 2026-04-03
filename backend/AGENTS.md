# AGENTS.md

## Scope

This file applies to work inside `backend/` and takes precedence over broader repo guidance for backend files.

access2 backend is being built as a production-oriented healthcare SaaS foundation.
Keep implementations small, explicit, and production-minded.

---

## Backend priorities

- Keep the backend as a clean modular monolith.
- Prefer straightforward code over clever abstractions.
- Optimize for maintainability and future SaaS evolution.
- Keep local development easy and portable to AWS or Google Cloud later.
- Treat this as real product code, not demo scaffolding.

---

## Required backend architecture rules

### Thin routes
FastAPI route handlers should:
- validate input
- call service-layer logic
- translate expected errors into HTTP responses

Do not place business logic directly in route handlers.

### Services own business behavior
Put business logic in `app/services`.

### Schemas stay explicit
Use Pydantic schemas for request and response models.
Prefer narrow, explicit update schemas over permissive payloads.

### Models stay focused
SQLAlchemy models should remain clear and simple.
Do not introduce unnecessary ORM complexity.

### Sync SQLAlchemy only
Use the existing synchronous SQLAlchemy session pattern unless explicitly asked to change it.

---

## Patterns to avoid unless explicitly requested

Do not introduce:
- repository pattern
- generic CRUD base classes
- RBAC frameworks
- policy engines
- event buses
- CQRS
- plugin systems
- microservices
- async database conversion
- premature multi-tenant abstractions beyond the requested slice

---

## Existing backend conventions to preserve

Unless the repo has already changed, preserve these patterns:

- FastAPI app under `app/`
- API routes under `app/api` and `app/api/v1`
- dependencies in `app/api/deps.py`
- models in `app/models`
- schemas in `app/schemas`
- services in `app/services`
- Alembic migrations under `alembic/versions`
- pytest tests under `tests/`

Auth conventions currently in place:
- JWT login endpoint exists
- current-user dependency exists
- superuser-only dependency exists
- inactive users cannot log in
- inactive users with previously issued tokens are blocked from protected endpoints

Do not weaken existing auth protections.

---

## Dependency note

Known working local auth dependency combination:

- `passlib[bcrypt]==1.7.4`
- `bcrypt==4.0.1`

Do not casually change this unless explicitly required.

---

## Database and migrations

- Any real model change should include an Alembic migration when appropriate.
- Reuse existing timestamp/base patterns.
- Keep migrations simple and readable.
- Prefer explicit uniqueness constraints where needed.
- Avoid hidden side effects in migrations.

When adding schema changes:
1. update SQLAlchemy model(s)
2. update Pydantic schema(s)
3. update service logic
4. update route wiring
5. add/update migration
6. add/update tests

---

## API design rules

- Reuse existing router and dependency patterns.
- Keep endpoint surfaces narrow.
- Return clear status codes and messages.
- Prefer explicit access checks through dependencies.
- Avoid broad admin mutation endpoints.

For updates:
- only expose fields that are intentionally allowed to change
- forbid unexpected extra fields where appropriate

---

## Testing rules

For backend slices, add or update focused pytest coverage.

Prefer tests that verify:
- access control
- endpoint behavior
- service behavior where useful
- regression protection for the requested slice

Do not claim tests passed unless they were actually run.

Typical commands:

```powershell
cd C:\dev\access2\backend
py -3 -m pytest tests/test_users.py -v
py -3 -m pytest