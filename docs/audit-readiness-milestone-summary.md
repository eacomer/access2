# Audit Readiness Milestone Summary

This milestone establishes the backend audit-readiness surface for ACCESS review packets. Its purpose is to make the persisted review packet workflow operationally visible, defensible for audit/payment review, and verifiable without rebuilding live packet data.

## What Is Implemented

- Immutable ACCESS review packet snapshots with stored `packet_json` and `packet_markdown`.
- Persisted snapshot event trail for creation, assignment, approval, rejection, and approved audit bundle exports.
- Deterministic `review_state` projection for snapshot lifecycle status.
- Deterministic `review_action` projection for actionable reviewer-pending snapshots.
- Patient audit-status projection with latest snapshot state, audit bundle status, `next_step`, and `completion_summary`.
- Patient backlog/drill-in wrapper that embeds the same audit-status projection.
- Org queue summary with both full snapshot-history lifecycle counts and latest-per-patient audit readiness rollup.
- Audit-readiness JSON worklist with latest-per-patient rows, filtering, pagination, deterministic ordering, and unfiltered `status_counts`.
- Audit-readiness CSV operational export for spreadsheet/audit-prep workflows.
- Approved-only audit bundle exports as JSON, Markdown, and PDF.
- Audit bundle verification against deterministic `audit_manifest` hashes.
- Snapshot detail `audit_timeline` derived from persisted events.
- Manual PowerShell validation guide for the audit-readiness API surface.

## Endpoint Inventory

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/reports/access-review-packet/snapshots/queue-summary` | Org operational queue and audit readiness summary. |
| `GET` | `/reports/access-review-packet/audit-readiness` | Latest-per-patient audit readiness JSON worklist. |
| `GET` | `/reports/access-review-packet/audit-readiness/export.csv` | Operational CSV export of audit readiness rows. |
| `GET` | `/reports/access-review-packet/patients/{patient_id}/audit-status` | Compact latest-snapshot audit status for one patient. |
| `GET` | `/reports/access-review-packet/snapshots/patient-backlog/{patient_id}` | Patient drill-in wrapper with `audit_status` and persisted snapshots. |
| `GET` | `/reports/access-review-packet/snapshots/patient-backlog/{patient_id}/latest` | Latest persisted snapshot for one patient. |
| `GET` | `/reports/access-review-packet/snapshots/my-pending` | Reviewer pending queue. |
| `GET` | `/reports/access-review-packet/reviewer/my-summary` | Reviewer workload summary. |
| `GET` | `/reports/access-review-packet/snapshots/{snapshot_id}` | Persisted snapshot detail with `audit_timeline`. |
| `GET` | `/reports/access-review-packet/snapshots/{snapshot_id}/events` | Persisted snapshot event trail. |
| `GET` | `/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle` | Approved snapshot audit bundle JSON. |
| `GET` | `/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/markdown` | Approved snapshot audit bundle Markdown. |
| `GET` | `/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/pdf` | Approved snapshot audit bundle PDF. |
| `POST` | `/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/verify` | Verify submitted manifest against persisted approved snapshot. |

## Important Contracts

### Latest-Per-Patient Readiness vs Full Snapshot-History Lifecycle

`audit_readiness_rollup`, patient audit-status, and the audit-readiness worklist use the latest persisted snapshot per patient. This prevents patients with historical snapshots from inflating readiness posture.

`snapshot_audit_lifecycle` in queue summary is intentionally different: it counts full snapshot-history lifecycle states for operational visibility.

### Operational Readiness CSV vs Approved Audit Bundle Export

`/audit-readiness/export.csv` is an operational readiness worklist export. It exports latest-per-patient readiness rows, is not paginated, and does not create `audit_bundle_exported` events.

Approved audit bundle exports are separate snapshot-level endpoints. Successful approved JSON, Markdown, and PDF audit bundle exports create persisted `audit_bundle_exported` events.

### Immutable Persisted Snapshot Reads

Snapshot-facing read endpoints return persisted snapshot rows and persisted event rows. They must not rebuild live packet data, mutate `packet_json`, or mutate `packet_markdown`.

Only newly created snapshots capture the current live packet state at creation time.

### Event Trail Rules

Snapshot events are persisted and tenant-scoped. Event reads are persisted-only and ordered deterministically by `created_at ASC`, then `id ASC`.

Current event types:

- `snapshot_created`
- `snapshot_assigned`
- `snapshot_approved`
- `snapshot_rejected`
- `audit_bundle_exported`

### Approved-Only Audit Bundle Rules

Audit bundle JSON, Markdown, PDF, and verification endpoints require an approved snapshot. Pending or rejected snapshots return the project-standard conflict behavior.

Audit manifests are generated from persisted snapshot content only. Verification compares submitted manifest values against recalculated persisted values and does not create export events.

## Validation

Focused review packet suite:

```powershell
cd C:\dev\access2\backend
py -3 -m pytest tests/test_access_review_packet.py -q
```

Latest validated result:

```text
91 passed
```

Broader related backend safety pass:

```powershell
cd C:\dev\access2\backend
py -3 -m pytest tests/test_access_review_packet.py tests/test_outcomes.py tests/test_patient_timeline.py tests/test_intervention_tasks.py -q
```

Latest validated result:

```text
281 passed
```

For manual API validation, use [manual-audit-readiness-api-validation.md](C:/dev/access2/docs/manual-audit-readiness-api-validation.md).

## Known Non-Goals

- No UI was added in this milestone.
- No live packet rebuilds happen on snapshot/audit-readiness read paths.
- No speculative analytics or scoring model was added.
- No broad architecture redesign was introduced.

## Future Work

These are suggested next development areas, not current contracts:

- Add tighter operational monitoring around failed audit bundle export attempts.
- Add admin-facing documentation for reviewing override-approved bundles.
- Add export retention and storage integration when file lifecycle requirements are defined.
- Add payer-specific packet variants only after concrete payer rules are known.
- Add deeper performance profiling for large tenant audit-readiness worklists.
