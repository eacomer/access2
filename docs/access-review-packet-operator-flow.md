# ACCESS Review Packet Operator Flow

Backend/API example flow for operators and reviewers using the ACCESS review packet workflow end to end.

Use this with the route reference in [access-review-packet-api.md](C:/dev/access2/docs/access-review-packet-api.md). For the backend audit-readiness milestone summary, see [audit-readiness-milestone-summary.md](C:/dev/access2/docs/audit-readiness-milestone-summary.md). For copy-paste manual validation of the audit-readiness API surface, see [manual-audit-readiness-api-validation.md](C:/dev/access2/docs/manual-audit-readiness-api-validation.md).

## Variables

PowerShell examples below use:

```powershell
$BACKEND_URL = "http://localhost:8000/api/v1"
$TOKEN = "<token>"
$PATIENT_ID = "<patient-id>"
$SNAPSHOT_ID = "<snapshot-id>"
$REVIEWER_USER_ID = "<reviewer-user-id>"

$Headers = @{
  Authorization = "Bearer $TOKEN"
}
```

## 1. Generate the live review packet

Use the live packet when you want the current patient evidence state before creating an immutable review artifact.

### Live JSON packet

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/$PATIENT_ID" `
  -Headers $Headers
```

### Live Markdown packet

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/$PATIENT_ID/markdown" `
  -Headers $Headers
```

Expected use:

- confirm current `review_readiness`
- confirm current case summary and evidence before freezing a snapshot

## 2. Create an immutable snapshot

Create a persisted review packet snapshot when the current packet should be preserved for review, audit, or payment justification.

```powershell
$Snapshot = Invoke-RestMethod `
  -Method Post `
  -Uri "$BACKEND_URL/reports/access-review-packet/$PATIENT_ID/snapshots" `
  -Headers $Headers

$SNAPSHOT_ID = $Snapshot.id
$Snapshot
```

Expected result:

- returns persisted snapshot metadata
- stores immutable `packet_json`
- stores immutable `packet_markdown`
- defaults `review_status` to `pending_review`

## 3. Assign the snapshot to a reviewer

Use assignment to route the pending review packet to a specific reviewer in the same organization.

```powershell
Invoke-RestMethod `
  -Method Patch `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/assignment" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    assigned_reviewer_user_id = $REVIEWER_USER_ID
  } | ConvertTo-Json)
```

Clear assignment:

```powershell
Invoke-RestMethod `
  -Method Patch `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/assignment" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    assigned_reviewer_user_id = $null
  } | ConvertTo-Json)
```

Expected result:

- `assigned_reviewer_user_id` updates
- `packet_json` does not change
- `packet_markdown` does not change

## 4. Reviewer opens the `my-pending` queue

The reviewer uses their own auth token and sees only snapshots assigned to them. By default, this queue returns only `pending_review`.

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/my-pending" `
  -Headers $Headers
```

Filter by readiness:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/my-pending?review_readiness_status=ready_for_review" `
  -Headers $Headers
```

Use pagination:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/my-pending?limit=25&offset=0" `
  -Headers $Headers
```

Expected result:

- excludes unassigned snapshots
- excludes snapshots assigned to other reviewers
- uses deterministic ordering:
  - `created_at desc`
  - `generated_at desc`
  - `id desc`

## 5. Reviewer views immutable Markdown

Open the stored Markdown for the assigned snapshot instead of regenerating current state.

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/markdown" `
  -Headers $Headers
```

Optional immutable JSON detail:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID" `
  -Headers $Headers
```

Expected result:

- returns stored snapshot content only
- includes `audit_timeline` on the JSON detail response
- does not rebuild the live packet

## 6. Reviewer approves the snapshot

Approve when the packet is ready for review completion or payment justification processing.

```powershell
Invoke-RestMethod `
  -Method Patch `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/review" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    review_status = "approved"
    review_note = "Evidence validated and approved."
  } | ConvertTo-Json)
```

Reject example:

```powershell
Invoke-RestMethod `
  -Method Patch `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/review" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    review_status = "rejected"
    review_note = "Additional outcome documentation required."
  } | ConvertTo-Json)
```

Expected result:

- updates `review_status`
- updates optional `review_note`
- stamps `reviewed_at`
- stamps `reviewed_by_user_id`
- leaves immutable packet content unchanged

If approval is blocked because the stored snapshot checklist has missing items, the API returns `409 Conflict`. A superuser can approve by exception with:

```powershell
Invoke-RestMethod `
  -Method Patch `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/review" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    review_status = "approved"
    decision_note = "Approved under documented exception."
    override_missing_checklist = $true
    override_reason = "Time-sensitive payer submission with documented missing closure evidence."
  } | ConvertTo-Json)
```

## 6a. Export the approved audit bundle

Use the audit bundle after approval when you need one persisted package for payer, compliance, or review defense.

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle" `
  -Headers $Headers
```

Expected result:

- works only for `approved` snapshots
- returns persisted `packet_json` and `packet_markdown`
- returns persisted `review_state`
- returns the persisted `approval_event`
- returns persisted decision events in deterministic order
- returns an `audit_manifest` with deterministic SHA-256 hashes for the persisted packet JSON and Markdown
- returns `export_metadata` with the recommended filename, content type, verification endpoint, and a per-request `generated_at` timestamp
- each successful json, markdown, or pdf export writes one persisted `audit_bundle_exported` snapshot event

Markdown export:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/markdown" `
  -Headers $Headers
```

PDF export:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/pdf" `
  -Headers $Headers `
  -OutFile "access-review-packet-audit-bundle-$SNAPSHOT_ID.pdf"
```

Manifest verification:

```powershell
$Bundle = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle" `
  -Headers $Headers

Invoke-RestMethod `
  -Method Post `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/verify" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body (@{
    audit_manifest = $Bundle.audit_manifest
  } | ConvertTo-Json -Depth 6)
```

## 7. Operator checks queue summary

Use the organization queue summary to monitor review workload, pending readiness posture, and assignment split.

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/queue-summary" `
  -Headers $Headers
```

Expected result includes:

- `total`
- `review_status`
- `review_readiness_status`
- `snapshot_audit_lifecycle`
- `audit_readiness_rollup`
- `snapshot_audit_lifecycle.pending_review_age`
- `assigned`
- `unassigned`
- `pending_review_assigned`
- `pending_review_unassigned`
- `pending_review_ready_for_review`
- `pending_review_active_open_work`
- `pending_review_incomplete`

Use `/reports/access-review-packet/audit-readiness` when you need the patient rows behind `audit_readiness_rollup`, filtered by latest-per-patient completion state such as `incomplete`, `review_ready`, `approved_not_exported`, `audit_ready`, or `rejected`. The response also includes `status_counts`, which matches `queue-summary.audit_readiness_rollup` and is not affected by filtering or pagination.

Use `/reports/access-review-packet/audit-readiness/export.csv` to export the same latest-per-patient rows as CSV for spreadsheet review. It accepts the same optional `status` filter and exports all matching rows without pagination. This is an operational readiness export, not an approved audit bundle export, and it does not write `audit_bundle_exported` events.

## 8. Reviewer checks personal pending workload

Use the reviewer summary to monitor only the authenticated reviewer’s assigned pending queue and its aging posture.

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/reviewer/my-summary" `
  -Headers $Headers
```

Expected result includes:

- `assigned_to_me_count`
- `pending_assigned_ready_count`
- `blocked_missing_evidence_count`
- `oldest_pending_snapshot_created_at`
- `pending_review_age`

`/reports/access-review-packet/snapshots/my-pending` also returns a per-item `review_action` hint so reviewers can distinguish ready work, missing evidence, and stale assigned reviews.

Shared snapshot responses may also expose `review_action`, but it is intentionally `null` for unassigned or terminal snapshot states.

## 9. Patient audit status

Use the patient audit-status endpoint when you need a compact view of the latest persisted review packet state and whether an approved audit bundle is available or already exported.

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/patients/<patient-id>/audit-status" `
  -Headers $Headers
```

Expected result includes:

- `has_snapshot`
- `latest_snapshot_id`
- `review_state`
- `review_action`
- `next_step`
- `completion_summary`
- `audit_bundle.available`
- `audit_bundle.exported`
- `audit_bundle.last_exported_at`
- `audit_bundle.export_formats`

## 10. Review event trail

Use the persisted event trail when you need to confirm who created, assigned, approved, or rejected a snapshot and what decision metadata was recorded.

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/events" `
  -Headers $Headers
```

Expected result:

- returns persisted events only
- uses deterministic ordering:
  - `created_at asc`
  - `id asc`
- includes assignment metadata such as `assigned_reviewer_user_id`
- includes review decision metadata such as `previous_review_status` and `new_review_status`
- does not rebuild or mutate stored `packet_json` or `packet_markdown`

## Optional operational queries

### Latest actionable queue

Get one latest pending packet per patient by default:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/latest-actionable" `
  -Headers $Headers
```

### Organization snapshot list

Inspect all persisted rows with filters:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots?review_status=pending_review&unassigned=true" `
  -Headers $Headers
```

### Patient backlog

Inspect latest snapshot state per patient:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/patient-backlog" `
  -Headers $Headers
```

For one patient, `GET /reports/access-review-packet/snapshots/patient-backlog/{patient_id}` returns a top-level object with `patient_id`, `audit_status`, and the filtered persisted `snapshots` list. It does not return a bare list.

## Minimal validation

From `C:\dev\access2\backend`:

```powershell
py -3 -m pytest tests/test_access_review_packet.py -q
```
