# ACCESS Review Packet API

Backend reference for the ACCESS review packet, immutable snapshot flow, and review/assignment queues.

## Core rules

- All routes are tenant-scoped.
- Cross-organization access returns the existing project-standard `403` or `404` depending on the route and resource lookup path.
- Live packet routes build current data.
- Snapshot routes return persisted rows only.
- Snapshot `packet_json` and `packet_markdown` are immutable after creation.
- Review and assignment updates only change snapshot metadata.
- Live packet and newly created snapshot payloads include a deterministic `review_checklist`.

## Status values

### `review_status`

- `pending_review`
- `approved`
- `rejected`

### `review_readiness_status`

- `ready_for_review`
- `active_open_work`
- `incomplete`

## Live packet endpoints

| Method | Route | Purpose | Key query params |
| --- | --- | --- | --- |
| `GET` | `/api/v1/reports/access-review-packet/{patient_id}` | Build the current JSON review packet for a patient. | None |
| `GET` | `/api/v1/reports/access-review-packet/{patient_id}/markdown` | Build the current Markdown review packet for a patient. | None |

### Review checklist

Live packets and newly created snapshot `packet_json` include:

- `review_checklist.overall_status`: `ready`, `warning`, or `missing`
- `review_checklist.ready_count`
- `review_checklist.warning_count`
- `review_checklist.missing_count`
- `review_checklist.items` with deterministic keys:
  - `has_signal`
  - `has_escalation`
  - `has_intervention`
  - `has_outcome`
  - `has_care_update`
  - `has_resolution`
  - `review_readiness`

## Patient snapshot endpoints

| Method | Route | Purpose | Key query params |
| --- | --- | --- | --- |
| `POST` | `/api/v1/reports/access-review-packet/{patient_id}/snapshots` | Persist a snapshot from the current live packet. | None |
| `GET` | `/api/v1/reports/access-review-packet/{patient_id}/snapshots` | List snapshots for one patient. | `review_status`, `limit`, `offset` |
| `GET` | `/api/v1/reports/access-review-packet/{patient_id}/snapshots/summary` | Patient-scoped review-status counts. | None |

## Snapshot detail endpoints

| Method | Route | Purpose | Key query params |
| --- | --- | --- | --- |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/{snapshot_id}` | Return one immutable persisted snapshot row. | None |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/markdown` | Return stored `packet_markdown` for a snapshot. | None |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle` | Return an approved-snapshot audit bundle from persisted snapshot and event rows only. | None |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/markdown` | Return the approved audit bundle as persisted-only Markdown. | None |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/pdf` | Return the approved audit bundle as a persisted-only PDF generated from the markdown audit bundle content. | None |
| `POST` | `/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/audit-bundle/verify` | Verify a submitted audit manifest against the persisted approved snapshot. | None |
| `PATCH` | `/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/review` | Update `review_status`, optional decision note, and optional approval override fields. | None |
| `PATCH` | `/api/v1/reports/access-review-packet/snapshots/{snapshot_id}/assignment` | Set or clear `assigned_reviewer_user_id`. | None |

Snapshot-facing JSON responses also include a deterministic `review_state` projection built from persisted snapshot rows plus persisted decision events only. Initial `review_state.state` values are:

- `pending_unassigned`
- `pending_assigned_ready`
- `blocked_missing_evidence`
- `approved`
- `approved_with_override`
- `rejected`

Snapshot detail responses also include `audit_timeline`, a read-only projection derived from persisted snapshot events with:

- `event_type`
- `occurred_at`
- `actor_user_id`
- `summary`

Persisted snapshot event types include:

- `snapshot_created`
- `snapshot_assigned`
- `snapshot_approved`
- `snapshot_rejected`
- `audit_bundle_exported`

Audit bundle rules:

- the audit bundle endpoint is tenant-scoped and persisted-only
- it returns `409 Conflict` unless the snapshot `review_status` is `approved`
- it never rebuilds `packet_json` or `packet_markdown`
- it includes persisted `review_state`, persisted `review_checklist`, the persisted approval event, and persisted decision events ordered by `created_at asc, id asc`
- the markdown audit bundle endpoint uses the same approval and tenant-scope rules and appends the stored immutable `packet_markdown`
- the pdf audit bundle endpoint uses the same approval and tenant-scope rules, generates from the persisted markdown audit bundle content, and returns `application/pdf`
- successful approved audit bundle exports for json, markdown, and pdf each write one persisted `audit_bundle_exported` event
- both audit bundle exports include an `audit_manifest` with deterministic SHA-256 hashes of persisted `packet_json` and `packet_markdown`
- both audit bundle exports include `export_metadata` describing the export contract, recommended filename, content type, source, and verification route
- `export_metadata.generated_at` may vary across reads, but `audit_manifest` remains deterministic for the same persisted snapshot
- the verify endpoint compares a submitted manifest to the recalculated persisted manifest and returns `expected` vs `actual` field mismatches

Approval gate:

- approving a snapshot checks persisted `packet_json.review_checklist.missing_count`
- if `missing_count > 0`, approval is blocked with `409 Conflict`
- a superuser may override missing checklist items by sending `override_missing_checklist=true` with a non-blank `override_reason`
- rejection remains allowed even when checklist items are missing
- approval never rebuilds or mutates stored `packet_json` or `packet_markdown`

### Review update request

```json
{
  "review_status": "approved",
  "review_note": "Ready for billing review.",
  "decision_note": "Ready for billing review.",
  "override_missing_checklist": false,
  "override_reason": null
}
```

Override approval example for an incomplete snapshot:

```json
{
  "review_status": "approved",
  "decision_note": "Approved under documented exception.",
  "override_missing_checklist": true,
  "override_reason": "Time-sensitive payer submission with documented missing closure evidence."
}
```

### Assignment update request

Assign:

```json
{
  "assigned_reviewer_user_id": "11111111-1111-1111-1111-111111111111"
}
```

Clear:

```json
{
  "assigned_reviewer_user_id": null
}
```

## Organization queue endpoints

| Method | Route | Purpose | Key query params |
| --- | --- | --- | --- |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/summary` | Organization-scoped review-status and readiness counts. | None |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/queue-summary` | Organization-scoped queue summary including pending breakdowns and assignment counts. | None |
| `GET` | `/api/v1/reports/access-review-packet/snapshots` | Organization-scoped persisted snapshot list. | `review_status`, `review_readiness_status`, `assigned_reviewer_user_id`, `unassigned`, `limit`, `offset` |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/latest-actionable` | One latest snapshot per patient, defaulting to `pending_review`. | `review_status`, `review_readiness_status`, `assigned_reviewer_user_id`, `unassigned`, `limit`, `offset` |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/my-pending` | Reviewer-scoped queue for the authenticated user, defaulting to `pending_review`. | `review_status`, `review_readiness_status`, `limit`, `offset` |
| `GET` | `/api/v1/reports/access-review-packet/reviewer/my-summary` | Reviewer-scoped pending workload summary for the authenticated user. | None |
| `GET` | `/api/v1/reports/access-review-packet/patients/{patient_id}/audit-status` | Patient-scoped latest snapshot audit/export status projection. | None |

`queue-summary` also includes `snapshot_audit_lifecycle`, a tenant-scoped persisted projection with counts for:

- `pending_unassigned_count`
- `pending_assigned_ready_count`
- `blocked_missing_evidence_count`
- `approved_count`
- `approved_with_override_count`
- `rejected_count`
- `approved_not_exported_count`
- `exported_count`

`snapshot_audit_lifecycle.pending_review_age` adds persisted aging buckets for pending lifecycle states only:

- `new_today_count`
- `one_to_three_days_count`
- `four_to_seven_days_count`
- `over_seven_days_count`

`reviewer/my-summary` returns reviewer-scoped pending workload counts derived from persisted snapshots only:

- `assigned_to_me_count`
- `pending_assigned_ready_count`
- `blocked_missing_evidence_count`
- `oldest_pending_snapshot_created_at`
- `pending_review_age`

`snapshots/my-pending` items also include `review_action`, a deterministic reviewer hint derived from persisted `review_state` and snapshot age:

- `ready_to_review`
- `missing_evidence`
- `stale_review`

`review_action` is `null` for non-reviewer-action states exposed by the shared snapshot response model:

- `pending_unassigned`
- `approved`
- `approved_with_override`
- `rejected`

`patients/{patient_id}/audit-status` returns a compact persisted status projection for the patient’s latest snapshot:

- `has_snapshot`
- `latest_snapshot_id`
- `latest_snapshot_created_at`
- `review_status`
- `review_state`
- `assigned_reviewer_user_id`
- `review_action`
- `next_step`
- `completion_summary`
- `audit_bundle.available`
- `audit_bundle.exported`
- `audit_bundle.last_exported_at`
- `audit_bundle.export_formats`
- `readiness_reasons`

### Patient audit-status readiness reasons

`readiness_reasons` is backend-owned structured explanatory data for why a patient is or is not audit-ready. It is returned by:

`GET /api/v1/reports/access-review-packet/patients/{patient_id}/audit-status`

Each reason has this shape:

| Field | Type | Notes |
| --- | --- | --- |
| `code` | `string` | Machine-readable reason code. |
| `severity` | `satisfied`, `missing`, `partial`, or `blocked` | Status for the proof element. |
| `label` | `string` | Display-friendly short reason label. |
| `detail` | `string` | Display-friendly explanation of the reason. |

Purpose:

- provide a backend-owned structured explanation of why the patient is or is not audit-ready
- keep the core audit-readiness reason logic in backend services instead of requiring frontend inference from scattered page data
- support the patient detail Outcome Proof Gaps panel

The frontend renders Outcome Proof Gaps from `readiness_reasons` when the field is available. Older responses without `readiness_reasons` may still be displayed by frontend fallback logic, but the API contract source of truth is the backend field.

The reasons reinforce the ACCESS2 evidence chain:

```text
signal → escalation → intervention → outcome → evidence → case summary → immutable review packet snapshot → approval/rejection → audit bundle → manifest verification
```

Known reason-code categories:

- signal
- escalation
- intervention
- outcome
- evidence
- snapshot/case summary
- review posture
- audit bundle availability/export status

V1 guardrail: `readiness_reasons` are read-only explanatory data. They must not imply frontend mutation controls for reviewer rejection or superuser override approval. ACCESS2 V1 may show those postures in the frontend, but reviewer rejection and superuser override approval mutation controls remain outside the read-only patient detail proof panels.

Synthetic/demo-safe example snippet:

```json
{
  "patient_id": "00000000-0000-4000-8000-000000000001",
  "has_snapshot": true,
  "review_status": "pending_review",
  "completion_summary": {
    "status": "incomplete",
    "missing_evidence_count": 2,
    "has_required_evidence": false,
    "has_approval": false,
    "has_export": false,
    "reason": "Snapshot is missing required evidence."
  },
  "audit_bundle": {
    "available": false,
    "exported": false,
    "last_exported_at": null,
    "export_formats": []
  },
  "readiness_reasons": [
    {
      "code": "signal_present",
      "severity": "satisfied",
      "label": "Signal",
      "detail": "At least one patient signal is present."
    },
    {
      "code": "outcome_present",
      "severity": "missing",
      "label": "Outcome",
      "detail": "No measured outcome is documented."
    },
    {
      "code": "audit_bundle_blocked_missing_evidence",
      "severity": "blocked",
      "label": "Audit bundle export",
      "detail": "Audit bundle export is blocked until missing evidence is resolved."
    }
  ]
}
```

## Patient backlog endpoints

| Method | Route | Purpose | Key query params |
| --- | --- | --- | --- |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/patient-backlog` | One latest snapshot row per patient with per-patient counts. | `review_status`, `review_readiness_status`, `limit`, `offset` |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/patient-backlog/{patient_id}` | Patient drill-in wrapper with `audit_status` plus persisted snapshots. | `review_status`, `review_readiness_status`, `limit`, `offset` |
| `GET` | `/api/v1/reports/access-review-packet/snapshots/patient-backlog/{patient_id}/latest` | Latest persisted snapshot for one patient. | `review_status`, `review_readiness_status` |
| `GET` | `/api/v1/reports/access-review-packet/audit-readiness` | Latest-per-patient audit readiness worklist. | `status`, `limit`, `offset` |
| `GET` | `/api/v1/reports/access-review-packet/audit-readiness/export.csv` | CSV export of the latest-per-patient audit readiness worklist. | `status` |

The patient drill-in route returns a top-level object, not a bare list:

- `patient_id`
- `audit_status`
- `snapshots`

`queue-summary` also includes `audit_readiness_rollup`, a latest-per-patient persisted rollup with:

- `incomplete_count`
- `review_ready_count`
- `approved_not_exported_count`
- `audit_ready_count`
- `rejected_count`

`/access-review-packet/audit-readiness` returns the latest persisted snapshot per patient with:

- `patient_id`
- `latest_snapshot_id`
- `latest_snapshot_created_at`
- `review_status`
- `review_state`
- `completion_status`
- `assigned_reviewer_user_id`
- `next_step`
- `audit_bundle`
- `status_counts`

`status_counts` matches `queue-summary.audit_readiness_rollup` for the tenant and is not affected by `status`, `limit`, or `offset`.

`/access-review-packet/audit-readiness/export.csv` is an operational readiness worklist export, not an approved audit bundle export. It exports all matching latest-per-patient audit-readiness rows as `text/csv; charset=utf-8`, is not paginated, does not rebuild packet data, and does not write `audit_bundle_exported` events. With no filter it uses `access-review-packet-audit-readiness.csv`; with `status` it uses `access-review-packet-audit-readiness-{status}.csv`.

CSV columns are stable for spreadsheet and audit-prep consumers:

- `patient_id`
- `latest_snapshot_id`
- `latest_snapshot_created_at`
- `review_status`
- `review_state`
- `completion_status`
- `assigned_reviewer_user_id`
- `next_step_action`
- `next_step_priority`
- `next_step_reason`
- `audit_bundle_available`
- `audit_bundle_exported`
- `audit_bundle_last_exported_at`
- `audit_bundle_export_formats`

## Ordering and pagination

### Snapshot list ordering

These endpoints use:

- `created_at desc`
- `generated_at desc`
- `id desc`

Applies to:

- patient snapshot list
- snapshot detail list endpoints
- org snapshot list
- reviewer `my-pending`

### Latest-per-patient ordering

These endpoints first select the latest snapshot per patient using:

- `created_at desc`
- `generated_at desc`
- `id desc`

Then order returned rows by:

- latest snapshot `created_at desc`
- `patient_id desc` as deterministic tie-breaker

Applies to:

- `latest-actionable`
- patient backlog

### Pagination

Queue/list endpoints support:

- `limit`: default `50`, min `1`, max `200`
- `offset`: default `0`

## Tenant scope behavior

- Patient-scoped routes first resolve the patient in the current tenant.
- Snapshot detail/update routes resolve the snapshot row and enforce tenant scope on that row.
- Organization queue routes count or list only persisted snapshot rows for `context.organization_id`.
- Assignment updates require the assigned reviewer, when present, to belong to the same organization.

## Immutability rule

After snapshot creation:

- `packet_json` does not change
- `packet_markdown` does not change

The following may change:

- `review_status`
- `review_note`
- `reviewed_at`
- `reviewed_by_user_id`
- `assigned_reviewer_user_id`

## Manual validation

From `C:\dev\access2\backend`:

```powershell
py -3 -m pytest tests/test_access_review_packet.py -q
py -3 -m pytest tests/test_access_case_summary.py -q
py -3 -m pytest tests/test_escalation_resolution.py -q
```

Useful route checks after local login:

```powershell
$ApiBase = "http://localhost:8000/api/v1"
$Headers = @{ Authorization = "Bearer <token>" }

Invoke-RestMethod -Method Get -Uri "$ApiBase/reports/access-review-packet/<patient-id>" -Headers $Headers
Invoke-RestMethod -Method Post -Uri "$ApiBase/reports/access-review-packet/<patient-id>/snapshots" -Headers $Headers
Invoke-RestMethod -Method Get -Uri "$ApiBase/reports/access-review-packet/snapshots/latest-actionable" -Headers $Headers
Invoke-RestMethod -Method Get -Uri "$ApiBase/reports/access-review-packet/snapshots/my-pending" -Headers $Headers
```
