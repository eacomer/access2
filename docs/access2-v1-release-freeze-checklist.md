# ACCESS2 V1 Release Freeze Checklist

Use this checklist before demo or release handoff. The goal is to preserve the validated ACCESS2 V1 production demo posture until there is an explicit V2 decision.

## Must Remain True

- Production frontend remains `https://access2.salvardata.com`.
- Production backend API remains `https://api.salvardata.com/api/v1`.
- Production E2E baseline remains `8 passed, 2 skipped, 0 failed`.
- Latest fresh production validation on 2026-05-11 returned `8 passed, 2 skipped, 0 failed` against `https://access2.salvardata.com`.
- The two skipped production E2E tests remain expected V1 read-only constraints:
  - Demo Patient 3 reviewer rejection through UI.
  - Demo Patient 4 superuser override approval through UI.
- Seeded demo data remains synthetic-only. No real PHI is entered or committed.
- The four seeded synthetic demo patients remain available and documented:
  - Demo Patient 1 - Audit Ready: `f4c31931-8fc2-41d6-9f45-9ab0bd039088`
  - Demo Patient 2 - Missing Evidence: `1c5c7db8-96f8-47af-a643-741641ecdcf3`
  - Demo Patient 3 - Rejected Review: `4c1ef5ef-1216-453d-b317-b965a0dd1dea`
  - Demo Patient 4 - Override Approval: `2e9dc25c-2e56-4d6a-aea0-8706d33b0444`
- Frontend demo posture remains read-only for V1.
- No approve, reject, override, export, assign, or create-snapshot mutation controls are added to the frontend.
- Audit bundles continue to use persisted snapshot, evidence, and event metadata only.
- Manifest verification remains part of the demo story.
- Railway backend startup command remains `bash scripts/render-start.sh`.
- No seed command is left as a Railway startup command.
- No secrets, tokens, database passwords, or real PHI are committed.

## Operator Pointers

- Run the stakeholder demo with [access2-v1-demo-day-script.md](C:/dev/access2/docs/access2-v1-demo-day-script.md).
- Validate handoff readiness with [access2-v1-demo-release-checklist.md](C:/dev/access2/docs/access2-v1-demo-release-checklist.md).
- Troubleshoot production E2E with [access2-railway-custom-domain-validation.md](C:/dev/access2/docs/access2-railway-custom-domain-validation.md).
- Recreate synthetic demo data with [access2-demo-data-recreation-checklist.md](C:/dev/access2/docs/access2-demo-data-recreation-checklist.md).
- Preserve scope with [access2-v1-scope-control.md](C:/dev/access2/docs/access2-v1-scope-control.md).

## Do Not Change Without Explicit V2 Direction

- Do not add real CMS submission, EHR/FHIR integration, billing, payment reconciliation, AI recommendations, predictive analytics, patient portal, provider messaging, broad admin features, or UI redesign work.
- Do not change Railway deployment configuration or backend startup command.
- Do not broaden the frontend from read-only audit posture into workflow mutation controls.
- Do not replace persisted review-packet or audit-bundle evidence with recomputed live-read behavior.
