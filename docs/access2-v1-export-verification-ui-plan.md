# ACCESS2 V1 Export and Verification UI Plan

## 1. Purpose

Plan the next ACCESS2 V1 frontend slice for audit bundle export and verification UI.

The goal is to let a reviewer or demo operator use existing backend audit bundle capabilities from the UI without expanding product scope, changing backend behavior, or implying broader mutation workflows are complete.

This slice should strengthen the V1 evidence path:

```text
review packet -> approval -> audit bundle export -> verification
```

## 2. Why This Comes Before Mutation UI

Export and verification UI is the lowest-risk next step because it can build on persisted review packet state and existing backend endpoints.

It comes before broader mutation UI because:

- It completes more of the audit evidence story without adding new workflow state transitions.
- It avoids approve, reject, assign, and create-snapshot controls in this slice.
- It makes the already-validated read-only audit posture demonstrable through controlled download and verification surfaces.
- It keeps mutation workflow readiness separate from audit artifact visibility.
- It reduces CMS-style review risk by showing what was exported and whether a supplied manifest verifies against persisted snapshot data.

## 3. Existing Backend Capabilities

Use existing backend capabilities only:

- `GET /reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle`
- `GET /reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/markdown`
- `GET /reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/pdf`
- `POST /reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/verify`

Important behavior to preserve:

- Snapshot data is immutable.
- Persisted `packet_json` and `packet_markdown` are not rebuilt during reads.
- Audit bundle verification compares supplied manifests against persisted snapshot data.
- Audit bundle export may create an `audit_bundle_exported` event only when using the existing successful audit bundle export endpoint behavior.
- Operational readiness CSV export is separate and must not create `audit_bundle_exported` events.

## 4. Proposed UI Surfaces

Add export and verification controls only where they naturally attach to an existing approved snapshot context.

Recommended surfaces:

- Patient detail review-packet backlog panel: show latest snapshot export options when a snapshot exists and is eligible for bundle access.
- Audit-readiness table row detail or row action area: expose bundle links for rows with an existing latest snapshot.
- Optional review-packet detail/read-only panel if one already exists in the current frontend structure.

UI elements should be explicit and narrow:

- Download audit bundle JSON.
- Download audit bundle Markdown.
- Download audit bundle PDF.
- Verify manifest against persisted snapshot data.
- Show verification result summary.

Avoid adding broad dashboard-level export controls unless they map directly to an existing snapshot.

## 5. User Flow

1. User starts from `/audit-readiness` or patient detail.
2. User identifies a patient or snapshot with review-packet evidence.
3. UI shows the snapshot identifier, review state, and export availability.
4. User selects one export format:
   - JSON bundle.
   - Markdown bundle.
   - PDF bundle.
5. Browser downloads or opens the selected artifact using the existing endpoint.
6. User can paste or upload a manifest payload for verification if the UI supports verification in the first slice.
7. UI posts the supplied manifest to the existing verification endpoint.
8. UI displays whether verification passed, failed, or could not run.
9. UI does not mutate snapshot content or rebuild packet content.

## 6. Read-Only and Audit Guardrails

- Do not add approve, reject, assign, or create-snapshot controls in this slice.
- Do not create generic mutation workflow controls.
- Do not rebuild snapshot data on read.
- Do not mutate `packet_json` or `packet_markdown`.
- Do not create events from read-only status, backlog, or verification display paths.
- Audit bundle export may log `audit_bundle_exported` only through existing successful export endpoint behavior.
- Operational readiness CSV export must remain separate and must not create `audit_bundle_exported` events.
- Keep tenant scoping and patient consistency intact.
- Keep deterministic ordering in patient audit and evidence displays.
- Surface errors as user-visible messages without hiding backend validation failures.

## 7. What Is Explicitly Out of Scope

- Approve/reject snapshot UI.
- Assign reviewer UI.
- Create-snapshot UI.
- New backend export endpoints.
- New backend verification semantics.
- Real CMS submission.
- EHR or FHIR integration.
- Billing, payment reconciliation, or payer submission workflows.
- AI recommendations or AI-generated evidence.
- Bulk export workflows.
- Operational readiness CSV changes.
- Broad review queue redesign.
- Generic case-management controls.

## 8. Minimal First Implementation Slice

Build the smallest useful UI slice:

1. Add frontend API helpers for the four existing audit bundle endpoints.
2. Add a compact export/verification section to the existing patient review-packet backlog panel or nearest existing snapshot context.
3. Show export links/buttons only when a snapshot id is available.
4. Add JSON, Markdown, and PDF download actions that call existing endpoints.
5. Add a simple manifest verification input and result display if it can be done without backend changes.
6. Add focused frontend helper tests.
7. Add or update Selenium smoke coverage only if the new UI is part of the critical demo path and can remain deterministic.

If verification input requires new backend shape discovery or unclear manifest authoring behavior, defer verification UI to a second narrow slice and implement download links first.

## 9. Acceptance Criteria

- Existing read-only audit surfaces still render.
- Patient detail still shows audit-status and review-packet backlog panels.
- Export UI appears only when an existing snapshot id is available.
- JSON, Markdown, and PDF controls use the existing backend endpoints.
- Verification UI, if included, uses the existing `POST .../verify` endpoint.
- No approve, reject, assign, or create-snapshot controls are added.
- Read-only status and backlog views remain non-mutating.
- Snapshot content and persisted packet content are not rebuilt by reads.
- Operational readiness CSV export behavior is unchanged and does not log audit bundle export events.
- Errors are visible and actionable.
- Tests cover frontend helpers and the minimal UI state added.

## 10. Test Plan

Recommended focused tests:

- Frontend API-helper tests for audit bundle JSON, Markdown, PDF, and verify calls.
- UI rendering test or component-level check if the project pattern supports it.
- Selenium smoke check for presence of export/verification UI on a seeded patient with a snapshot, if deterministic seeded data is available.
- Manual demo check from `docs/access2-v1-demo-runbook.md`.

Regression checks:

- Existing frontend API-helper tests.
- Existing read-only Selenium smoke command:

```powershell
py -3 -m pytest tests/e2e/test_access2_smoke.py --e2e-base-url http://localhost:3001 -q -rs
```

Backend regression tests are not required for a frontend-only slice unless the implementation uncovers a backend defect. If backend behavior changes become necessary, stop and report before expanding scope.

## 11. Risks and Mitigations

- Risk: Export controls are mistaken for broad mutation workflow completion.
  - Mitigation: Label the section as audit bundle export/verification only and keep approve/reject/assign/create-snapshot out of scope.

- Risk: Verification UI is unclear without an obvious manifest source.
  - Mitigation: Start with download links, then add verification in a second slice if manifest input needs clarification.

- Risk: Export endpoint event logging is misunderstood.
  - Mitigation: Document that `audit_bundle_exported` may be created only by existing successful audit bundle export endpoint behavior.

- Risk: Operational readiness CSV export is conflated with audit bundle export.
  - Mitigation: Keep CSV export separate and do not route it through audit bundle export behavior.

- Risk: Seeded demo data lacks an eligible snapshot.
  - Mitigation: Gate UI on snapshot presence and document empty/read-only states clearly.

## 12. Recommended Codex Implementation Prompt

```text
We are continuing ACCESS2 V1. Before making changes, read AGENTS.md, docs/access2-v1-scope-control.md, docs/access2-v1-export-verification-ui-plan.md, docs/access2-v1-demo-runbook.md, and tests/e2e/README.md.

Implement the minimal frontend-only export/verification UI slice using existing backend endpoints:
- GET /reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle
- GET /reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/markdown
- GET /reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/pdf
- POST /reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/verify

Do not change backend code. Do not change audit workflow behavior. Do not add approve/reject/assign/create-snapshot controls. Do not imply mutation workflows are complete. Preserve snapshot immutability, persisted packet_json/packet_markdown, tenant scoping, deterministic reads, and read-only endpoint behavior.

Prefer the smallest useful frontend slice:
1. Add frontend API helpers for existing audit bundle endpoints.
2. Add compact export controls in the existing patient review-packet backlog or nearest existing snapshot context.
3. Add verification UI only if it can use the existing verify endpoint without backend changes.
4. Add focused frontend tests.
5. Run relevant frontend tests and the seeded read-only Selenium smoke if practical.

If backend changes, generated artifacts, or unrelated product code appear required, stop and report instead of expanding scope.
```
