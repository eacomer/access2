# ACCESS2 V1 Demo Handoff Summary

## Status

ACCESS2 V1 is ready to demo when the documented local prerequisites are satisfied.

Use this handoff with:

- [access2-v1-demo-release-checklist.md](C:/dev/access2/docs/access2-v1-demo-release-checklist.md)
- [access2-v1-demo-runbook.md](C:/dev/access2/docs/access2-v1-demo-runbook.md)
- [access2-v1-frontend-demo-script.md](C:/dev/access2/docs/access2-v1-frontend-demo-script.md)
- [access2-railway-demo-validation.md](C:/dev/access2/docs/access2-railway-demo-validation.md)
- [access2-railway-custom-domain-validation.md](C:/dev/access2/docs/access2-railway-custom-domain-validation.md)

The validated V1 path is:

```text
login -> patient/worklist -> intervention/outcome evidence -> review packet -> approval -> audit bundle export -> verification
```

## What The Demo Proves

- A seeded operator can sign in.
- Authenticated users can open patient/worklist surfaces.
- Operators can view organization-level audit readiness.
- Operators can open the Demo Release Summary and explain the read-only Evidence Proof Checklist across the four seeded synthetic demo patients.
- Operators can open patient detail and review patient-level audit status.
- Operators can inspect the review-packet backlog for persisted snapshots.
- Approved export-ready snapshots expose JSON, Markdown, and PDF audit bundle downloads.
- A copied JSON bundle `audit_manifest` can be verified against persisted snapshot data.

## Validated Local Prerequisites

- Docker Desktop is running.
- Docker Compose stack is running.
- Backend live and ready health checks pass.
- Frontend runs at `http://localhost:3001`.
- Backend auth is reachable.
- Documented local credentials work:

```text
admin@example.com / Admin123!
```

- Patients exist in the local demo database.
- At least one patient has a persisted review-packet snapshot.
- At least one snapshot is approved and export-ready.
- A real JSON audit bundle `audit_manifest` is available for verification.

## Final Validation Evidence

Backend health:

- `/api/v1/health/live`: HTTP 200
- `/api/v1/health/ready`: HTTP 200
- Database: ok
- Redis: ok

Frontend and auth:

- `http://localhost:3001/login`: HTTP 200
- Login succeeded with `admin@example.com / Admin123!`
- Authenticated navigation showed `Patients`, `Audit Readiness`, and `Verify Bundle`

Demo data:

- Patient: `ef77cbcc-778a-43e5-9274-36e3565d0aeb`
- Snapshot: `f1d03ed0-30a0-4f3a-9b24-2a13db200f95`
- Completion: `audit_ready`
- Bundle available/exported: `true`
- Formats: `json`, `markdown`, `pdf`

Bundle downloads through the frontend proxy:

- JSON: HTTP 200, `application/json`, 9754 bytes
- Markdown: HTTP 200, `text/markdown; charset=utf-8`, 4136 bytes
- PDF: HTTP 200, `application/pdf`, 6047 bytes

Verification states:

- Verified manifest: passed
- Mismatch: passed
- Invalid JSON: passed
- Missing-field request error: passed
- Unauthenticated verification request: HTTP 401

Selenium smoke:

```text
5 passed, 9 skipped
```

The skipped tests are expected for the read-only smoke command unless the documented data-creating bootstrap flag is supplied.

Production Railway E2E:

```text
8 passed, 2 skipped, 0 failed
```

The two skipped production tests remain expected V1 read-only constraints for Demo Patient 3 reviewer rejection through UI and Demo Patient 4 superuser override approval through UI.

## Known Non-Blocking Warnings

- `backend/.tmp/pytest_cache` permission warnings may appear in `git status` or backend watchfiles logs.
- `frontend/.env.local` must remain uncommitted.
- `frontend/tsconfig.tsbuildinfo` must remain uncommitted.
- Windows LF/CRLF Git warnings may appear when docs are touched.

## Demo Risks And Prerequisites

- The seeded local database state must be preserved or recreated through documented local paths.
- Bundle downloads require an approved export-ready snapshot.
- Verification requires a real `audit_manifest` copied from an exported JSON audit bundle.
- `localhost:3000` can be stale; use the documented helper and `http://localhost:3001` for controlled demos.
- If login shows `Unable to sign in right now. Please try again.`, verify Docker, backend health, frontend API base URL, and seeded auth.
- For production E2E failures, use the troubleshooting path in [access2-railway-custom-domain-validation.md](C:/dev/access2/docs/access2-railway-custom-domain-validation.md) before changing product code.

## Do Not Change Before Demo

- Do not add new product scope.
- Do not change approval, export, or verification logic.
- Do not alter demo data unless intentionally reseeding through documented paths.
- Do not commit local/generated files.
- Do not introduce AI, predictive analytics, EHR/FHIR, billing, broad admin features, or UI redesign work during demo stabilization.

## Recommended Next Phase

After the V1 demo, run post-demo backlog triage against observed operator feedback and validation notes. Keep new work as explicitly scoped follow-up slices; do not expand the demo stabilization branch into AI, EHR/FHIR, billing, predictive analytics, or broad UI redesign without a separate approved direction.
