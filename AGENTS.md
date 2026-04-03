
# AGENTS.md

## Project overview

access2 is a production-oriented healthcare SaaS application under active development.

Current phase:
- early backend foundation
- production-minded architecture
- local-first development
- designed to lift and shift cleanly to AWS or Google Cloud later

This is **not** a throwaway demo app. Build each slice as if it may become part of a real provider-facing SaaS platform.

---

## Primary architecture goals

- Keep the backend modular, simple, and production-minded.
- Prefer a **modular monolith** over premature microservices.
- Keep business logic out of API route handlers.
- Keep deterministic application logic clearly separated from future AI-assisted functionality.
- Optimize for maintainability, readability, and incremental extension.
- Avoid lock-in to local-only assumptions or cloud-vendor-specific abstractions.

---

## Backend stack

- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Redis
- Pydantic v2
- Sync SQLAlchemy session pattern for now
- Docker Compose for local development

---

## Repository structure

Assume this general structure unless the repo has evolved:

- `backend/app/core` → config, security, database, logging
- `backend/app/api` → FastAPI routing and dependencies
- `backend/app/api/v1` → versioned API endpoints
- `backend/app/models` → SQLAlchemy models
- `backend/app/schemas` → Pydantic schemas
- `backend/app/services` → business logic
- `backend/alembic` → migrations
- `backend/tests` → pytest coverage
- `frontend/` → frontend app
- `infra/` → docker and local infra scripts

Before making changes, inspect the real repo structure and adapt to what actually exists.

---

## Working principles for Codex

### 1) Inspect first
Always inspect the real files first before proposing changes.
Do not assume the repo matches earlier examples or prior drafts.

### 2) Keep slices small
Implement only the requested slice.
Do not bundle unrelated improvements.

### 3) Keep routes thin
FastAPI route handlers should:
- validate input
- call service-layer logic
- translate expected errors into HTTP responses

Do not place core business logic in route functions.

### 4) Keep business logic in services
Put application behavior in `app/services`.

### 5) Use sync SQLAlchemy
Use the existing synchronous SQLAlchemy pattern unless the prompt explicitly asks to change it.

### 6) Prefer minimal clean abstractions
Do **not** introduce:
- repository pattern
- service base classes
- RBAC frameworks
- event buses
- CQRS layers
- plugin frameworks
- premature domain abstraction

unless explicitly requested.

### 7) Stay production-minded without overengineering
Choose the simplest implementation that would still make sense in an early production SaaS backend.

### 8) Preserve cloud portability
Do not add designs that make local development or cloud migration unnecessarily hard.
Prefer environment-driven configuration and portable dependencies.

---

## Current standing backend conventions

Unless the repo has already changed, preserve these conventions:

- JWT auth is already implemented
- `/api/v1/auth/login` and `/api/v1/auth/me` exist
- `get_current_user` dependency exists
- `get_current_superuser` exists for admin-only routes
- user-management hardening exists
- inactive users cannot log in
- inactive users with old tokens are blocked from protected endpoints
- password hashing uses passlib with bcrypt pinned for compatibility

If changing auth-adjacent code, verify behavior against the actual current implementation.

---

## Dependency and compatibility notes

Known local compatibility note:
- `passlib[bcrypt]==1.7.4`
- `bcrypt==4.0.1`

Do not casually upgrade bcrypt unless explicitly asked.
If dependency changes are needed, explain why and keep them minimal.

---

## Database and migration rules

- All persistent model changes must include an Alembic migration when appropriate.
- Keep migrations straightforward and reversible when practical.
- Reuse existing declarative base and timestamp patterns.
- Prefer explicit constraints for important uniqueness rules.
- Do not introduce complex tenancy, audit, or policy frameworks unless explicitly requested.

---

## API design rules

- Reuse existing API versioning and router patterns.
- Keep response models explicit.
- Keep update surfaces narrow and intentional.
- Prefer explicit schemas over permissive generic payloads.
- Use clean HTTP status codes and clear error messages.
- Keep security boundaries obvious in route dependencies.

---

## Testing expectations

For backend changes, add or update focused pytest coverage.

Prefer:
- endpoint tests
- service behavior tests where useful
- regression coverage for access-control rules
- tests that prove new behavior without over-mocking

Do not remove existing passing tests unless they are truly obsolete and the reason is documented.

After changes, run the smallest relevant test set first, then broader tests.

Typical commands:

```powershell
cd C:\dev\access2\backend
py -3 -m pytest tests/test_users.py -v
py -3 -m pytest

## Protected areas

Do not change these without explicit request:
- authentication flow shape
- JWT settings and token structure
- database session pattern
- Docker Compose service topology
- environment variable names already in active use

If a requested change appears to require one of these, stop and call it out explicitly in findings before modifying it.