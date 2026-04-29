# Manual Audit Readiness API Validation

Use this guide to manually validate the persisted audit-readiness workflow from PowerShell. These checks are read-oriented except for approved audit bundle exports, which intentionally write `audit_bundle_exported` events for JSON, Markdown, and PDF bundle exports.

Important distinctions:

- Audit-readiness CSV is an operational readiness worklist export, not an approved snapshot audit bundle export.
- Audit-readiness endpoints are read-only and do not write `audit_bundle_exported` events.
- Audit bundle exports require an approved snapshot; pending or rejected snapshots should return `409 Conflict`.
- Patient audit-status and patient drill-in use the latest persisted snapshot state.
- No endpoint in this guide should rebuild live packet data or mutate snapshot `packet_json` / `packet_markdown`.

## 1. Set Variables

Set `BACKEND_URL` to the API v1 base URL.

```powershell
$BACKEND_URL = "http://localhost:8000/api/v1"
$TOKEN = "<access-token>"
$PATIENT_ID = "<patient-id>"
$SNAPSHOT_ID = "<snapshot-id>"
$STATUS = "audit_ready"

$Headers = @{
  Authorization = "Bearer $TOKEN"
}
```

Allowed `STATUS` values for audit-readiness filters:

- `incomplete`
- `review_ready`
- `approved_not_exported`
- `audit_ready`
- `rejected`

## 2. Check Org Queue Summary

```powershell
$QueueSummary = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/queue-summary" `
  -Headers $Headers

$QueueSummary.snapshot_audit_lifecycle
$QueueSummary.audit_readiness_rollup
```

Expected checks:

- `snapshot_audit_lifecycle` shows full snapshot-history operational counts.
- `audit_readiness_rollup` shows latest-per-patient readiness counts.
- Reads should not create snapshot events.

## 3. Check Audit-Readiness JSON Worklist

```powershell
$AuditReadiness = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/audit-readiness" `
  -Headers $Headers

$AuditReadiness.status_counts
$AuditReadiness.items | Select-Object `
  patient_id,
  latest_snapshot_id,
  latest_snapshot_created_at,
  review_status,
  review_state,
  completion_status,
  assigned_reviewer_user_id
```

Expected checks:

- `items` contains latest persisted snapshot rows per patient only.
- `status_counts` should match `QueueSummary.audit_readiness_rollup`.
- The endpoint is paginated by default, but `status_counts` is not affected by pagination.

## 4. Check Filtered Audit-Readiness Rows

```powershell
$FilteredAuditReadiness = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/audit-readiness?status=$STATUS" `
  -Headers $Headers

$FilteredAuditReadiness.total_count
$FilteredAuditReadiness.items | Select-Object `
  patient_id,
  latest_snapshot_id,
  completion_status,
  review_state
```

Expected checks:

- Every row has `completion_status` equal to `$STATUS`.
- `total_count` reflects the filtered row count.
- `status_counts` remains the full tenant-scoped distribution.

## 5. Export Audit-Readiness CSV

Unfiltered export:

```powershell
Invoke-WebRequest `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/audit-readiness/export.csv" `
  -Headers $Headers `
  -OutFile ".\access-review-packet-audit-readiness.csv"
```

Filtered export:

```powershell
Invoke-WebRequest `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/audit-readiness/export.csv?status=$STATUS" `
  -Headers $Headers `
  -OutFile ".\access-review-packet-audit-readiness-$STATUS.csv"
```

Inspect CSV rows:

```powershell
Import-Csv ".\access-review-packet-audit-readiness-$STATUS.csv" |
  Select-Object `
    patient_id,
    latest_snapshot_id,
    latest_snapshot_created_at,
    review_status,
    review_state,
    completion_status,
    assigned_reviewer_user_id,
    next_step_action,
    next_step_priority,
    audit_bundle_available,
    audit_bundle_exported,
    audit_bundle_export_formats
```

Expected checks:

- Response content type is `text/csv; charset=utf-8`.
- Unfiltered filename is `access-review-packet-audit-readiness.csv`.
- Filtered filename is `access-review-packet-audit-readiness-{status}.csv`.
- CSV exports all matching rows and is not paginated.
- CSV row ordering matches the JSON worklist before pagination: `latest_snapshot_created_at desc`, then `latest_snapshot_id asc`.
- CSV export does not write `audit_bundle_exported` events.

## 6. Check Patient Audit-Status

```powershell
$PatientAuditStatus = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/patients/$PATIENT_ID/audit-status" `
  -Headers $Headers

$PatientAuditStatus
$PatientAuditStatus.audit_bundle
$PatientAuditStatus.next_step
$PatientAuditStatus.completion_summary
```

Expected checks:

- The response uses the patient’s latest persisted snapshot.
- `audit_bundle.available` is true only for approved or override-approved snapshots.
- `audit_bundle.exported` is based on persisted `audit_bundle_exported` events.
- `next_step` and `completion_summary` match the latest snapshot posture.

## 7. Check Patient Backlog / Drill-In Wrapper

```powershell
$PatientBacklog = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/patient-backlog/$PATIENT_ID" `
  -Headers $Headers

$PatientBacklog.patient_id
$PatientBacklog.audit_status
$PatientBacklog.snapshots | Select-Object `
  id,
  review_status,
  review_readiness_status,
  assigned_reviewer_user_id,
  created_at
```

Expected checks:

- The top-level response is an object with `patient_id`, `audit_status`, and `snapshots`.
- `audit_status` matches the standalone patient audit-status endpoint.
- `snapshots` contains persisted snapshot backlog rows.
- Patients with no snapshots return `audit_status.has_snapshot = false` and `snapshots = @()`.

## 8. Check Snapshot Detail

```powershell
$SnapshotDetail = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID" `
  -Headers $Headers

$SnapshotDetail.review_status
$SnapshotDetail.review_state
$SnapshotDetail.review_action
$SnapshotDetail.audit_timeline
```

Expected checks:

- Snapshot detail returns persisted `packet_json` and `packet_markdown`.
- `audit_timeline` is derived from persisted snapshot events.
- `review_action` is populated only for actionable pending reviewer states.
- This read should not create events or rebuild packet data.

## 9. Check Snapshot Events

```powershell
$SnapshotEvents = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/events" `
  -Headers $Headers

$SnapshotEvents.events | Select-Object `
  event_type,
  created_at,
  actor_user_id,
  metadata
```

Expected checks:

- Events are persisted-only.
- Ordering is deterministic by `created_at asc`, then `id asc`.
- Expected event types include lifecycle events such as `snapshot_created`, `snapshot_assigned`, `snapshot_approved`, `snapshot_rejected`, and approved audit bundle export events when present.

## 10. Export Approved Audit Bundle JSON

Use this only with an approved snapshot.

```powershell
$AuditBundle = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle" `
  -Headers $Headers

$AuditBundle.review_status
$AuditBundle.review_state
$AuditBundle.audit_manifest
$AuditBundle.export_metadata
```

Expected checks:

- `review_status` is `approved`.
- `audit_manifest` contains deterministic hashes for persisted `packet_json` and `packet_markdown`.
- This successful approved audit bundle export writes one `audit_bundle_exported` event with `export_format = json`.

## 11. Export Approved Audit Bundle Markdown

Use this only with an approved snapshot.

```powershell
$MarkdownResponse = Invoke-WebRequest `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/markdown" `
  -Headers $Headers

$MarkdownResponse.Content | Set-Content ".\access-review-packet-audit-bundle-$SNAPSHOT_ID.md"
$MarkdownResponse.Content
```

Expected checks:

- Markdown includes `ACCESS Review Packet Audit Bundle`.
- Markdown includes `Export Metadata`, `Audit Manifest`, `Review Checklist`, `Decision Event Trail`, and `Immutable Review Packet`.
- This successful approved audit bundle export writes one `audit_bundle_exported` event with `export_format = markdown`.

## 12. Export Approved Audit Bundle PDF

Use this only with an approved snapshot.

```powershell
$PdfPath = ".\access-review-packet-audit-bundle-$SNAPSHOT_ID.pdf"

Invoke-WebRequest `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/pdf" `
  -Headers $Headers `
  -OutFile $PdfPath

Get-Item $PdfPath | Select-Object FullName, Length
```

Expected checks:

- Response content type is `application/pdf`.
- Response filename is `access-review-packet-audit-bundle-{snapshot_id}.pdf`.
- The file starts with PDF signature bytes `%PDF`.
- This successful approved audit bundle export writes one `audit_bundle_exported` event with `export_format = pdf`.

Optional PDF signature check:

```powershell
$Bytes = Get-Content $PdfPath -Encoding Byte -TotalCount 4
[Text.Encoding]::ASCII.GetString($Bytes)
```

Expected output:

```text
%PDF
```

## 13. Verify Audit Bundle Manifest

First get the approved audit bundle JSON and extract its manifest:

```powershell
$AuditBundle = Invoke-RestMethod `
  -Method Get `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle" `
  -Headers $Headers

$VerifyBody = @{
  audit_manifest = $AuditBundle.audit_manifest
} | ConvertTo-Json -Depth 10
```

Then submit the manifest for verification:

```powershell
$Verification = Invoke-RestMethod `
  -Method Post `
  -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/verify" `
  -Headers $Headers `
  -ContentType "application/json" `
  -Body $VerifyBody

$Verification
```

Expected checks:

- `verified` is `true`.
- `mismatches` is empty.
- `expected_manifest` matches the submitted approved bundle manifest.
- Verification does not create `audit_bundle_exported` events.

## 14. Expected 409 Conflict for Pending or Rejected Snapshots

Set `$SNAPSHOT_ID` to a pending or rejected snapshot before running these checks.

JSON bundle conflict:

```powershell
try {
  Invoke-RestMethod `
    -Method Get `
    -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle" `
    -Headers $Headers
} catch {
  $_.Exception.Response.StatusCode.value__
}
```

Markdown bundle conflict:

```powershell
try {
  Invoke-RestMethod `
    -Method Get `
    -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/markdown" `
    -Headers $Headers
} catch {
  $_.Exception.Response.StatusCode.value__
}
```

PDF bundle conflict:

```powershell
try {
  Invoke-WebRequest `
    -Method Get `
    -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/pdf" `
    -Headers $Headers
} catch {
  $_.Exception.Response.StatusCode.value__
}
```

Verification conflict:

```powershell
try {
  Invoke-RestMethod `
    -Method Post `
    -Uri "$BACKEND_URL/reports/access-review-packet/snapshots/$SNAPSHOT_ID/audit-bundle/verify" `
    -Headers $Headers `
    -ContentType "application/json" `
    -Body (@{
      audit_manifest = @{
        snapshot_id = $SNAPSHOT_ID
        patient_id = $PATIENT_ID
        review_status = "approved"
        generated_from = "persisted_snapshot"
        packet_json_sha256 = "invalid"
        packet_markdown_sha256 = "invalid"
        decision_event_count = 0
        approval_event_id = "invalid"
        approval_override_used = $false
      }
    } | ConvertTo-Json -Depth 10)
} catch {
  $_.Exception.Response.StatusCode.value__
}
```

Expected output for each conflict check:

```text
409
```
