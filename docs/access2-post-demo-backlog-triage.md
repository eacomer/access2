# ACCESS2 Post-Demo Backlog Triage

## Purpose

Use this triage note after the validated ACCESS2 V1 demo to sort follow-up work without expanding scope during demo stabilization.

This document separates:

- critical demo blockers
- small demo polish and reliability improvements
- post-demo V1 hardening
- later V2 candidates
- items explicitly out of scope for now

## Current V1 Demo-Ready Baseline

ACCESS2 V1 is demo-ready when the documented local prerequisites are satisfied.

Validated path:

```text
login -> patient/worklist -> intervention/outcome evidence -> review packet -> approval -> audit bundle export -> verification
```

Validated frontend surfaces include login, Patients, Audit Readiness, patient detail, patient audit-status, review-packet backlog, approved-only JSON/Markdown/PDF bundle downloads, and audit bundle verification.

## Critical Blockers Before Demo

None known in the current validated local demo state.

The demo still depends on these prerequisites:

- Docker Desktop and backend services are running.
- Backend live and ready health checks pass.
- Auth is seeded and `admin@example.com / Admin123!` can sign in.
- Patients exist in the local demo database.
- At least one patient has a persisted review-packet snapshot.
- At least one snapshot is approved and export-ready.
- A real JSON audit bundle `audit_manifest` is available for verification.

If any of those prerequisites are missing, treat that as an environment or demo-data blocker, not a reason to add product scope during stabilization.

## Demo Polish / Reliability Candidates

These are small improvements that support the current validated path:

- Reduce or document local pytest cache permission warnings if practical.
- Make the demo data recreation path easier to follow from the runbook.
- Add clearer operator guidance for the approved export-ready snapshot prerequisite.
- Add a short reset/reseed note only if it uses repo-supported commands that already exist.
- Add screenshots to the demo script only after confirming they match the current UI.
- Tighten wording around unavailable bundle downloads for non-approved snapshots if operator feedback shows confusion.

Do not use this category for broad UI redesign.

## Post-Demo V1 Hardening Candidates

These are production-minded follow-ups that still fit the V1 evidence and audit path:

- Create a more deterministic demo seed path for one approved export-ready snapshot.
- Add targeted backend/frontend regression coverage around the fully verified demo path if gaps remain.
- Review environment variable documentation for local backend/frontend auth wiring.
- Improve operator-facing error handling text where current messages are technically correct but unclear.
- Add audit-readiness edge-case tests for empty rows, no approved snapshots, exported snapshots, and rejected snapshots.
- Add or confirm export/verification negative-path tests for unsupported formats, missing auth, mismatched manifests, and missing manifest fields.
- Add deployment-readiness notes for a later cloud lift-and-shift review, without implementing cloud infrastructure in this slice.

## Later V2 Candidates

These are candidates for later planning after V1 demo feedback is reviewed:

- Richer reviewer workflow UX.
- Role and permission refinement.
- Organization-level reporting improvements beyond audit readiness.
- Production deployment pipeline.
- Deeper operational analytics tied to validated workflow evidence.
- Integrations only after V1 scope is reviewed and explicitly approved.

These are not part of demo stabilization.

## Explicitly Out Of Scope For Now

Do not start these during V1 demo stabilization:

- AI or predictive analytics.
- EHR/FHIR integrations.
- Billing or payment workflows.
- Broad admin console work.
- Broad UI redesign.
- New workflow mutation controls.
- Changes to approval, export, or verification rules.
- Real CMS submission integration.

## Recommended Next Smallest Slice

Recommended next slice: create a docs-only demo data recreation checklist.

Scope for that slice:

- Use only existing documented commands and API/operator-flow steps.
- Explain how to recreate the local demo prerequisites from a disposable database.
- Include the persisted snapshot and approved export-ready snapshot prerequisites.
- Do not add scripts, endpoints, UI, or new mutation controls.

This is preferred over a seed helper until post-demo feedback confirms that a code/script change is worth the added maintenance surface.

## Definition Of Ready For Next Work

A follow-up slice is ready when:

- The V1 demo is completed or stakeholder feedback is captured.
- Current demo state is preserved, or reseeding is documented.
- One backlog item is selected from this triage note.
- Scope is checked against [access2-v1-scope-control.md](C:/dev/access2/docs/access2-v1-scope-control.md).
- The slice can be completed without changing unrelated backend, frontend, test, or generated files.
