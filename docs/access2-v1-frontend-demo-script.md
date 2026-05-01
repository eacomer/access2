# ACCESS2 V1 Frontend Demo Script

## Purpose

Use this script to walk a beginner operator or evaluator through the current ACCESS2 V1 frontend audit path:

```text
login -> audit readiness -> patient detail -> audit status -> review packet backlog -> audit bundle download -> verification
```

This is a frontend demo script. It does not add backend behavior, create snapshots, approve reviews, assign reviewers, or change audit data.

## Preconditions

- Backend and frontend are running against a local demo or seeded database.
- Backend auth must be reachable before the frontend steps can proceed past sign-in.
- The operator has a valid ACCESS2 account. The established local demo account is:

```text
admin@example.com / Admin123!
```

- At least one patient has persisted review-packet snapshot data.
- Audit bundle downloads require an approved snapshot. If no approved snapshot exists, the demo can still show why download actions are unavailable.
- Verification requires an `audit_manifest` copied from an exported JSON audit bundle.

Local generated files may exist but must remain uncommitted:

```text
frontend/.env.local
frontend/tsconfig.tsbuildinfo
```

## Local Commands

Use the established demo frontend helper when running a controlled local demo:

```powershell
cd C:\dev\access2
.\scripts\start-access2-demo-frontend.ps1
```

Typical local frontend URL:

```text
http://localhost:3001
```

Frontend validation commands, if source files are changed:

```powershell
cd C:\dev\access2\frontend
& 'C:\Program Files\nodejs\npm.cmd' test
& 'C:\Program Files\nodejs\npm.cmd' run lint
& 'C:\Program Files\nodejs\npm.cmd' run build
& 'C:\Program Files\nodejs\npx.cmd' tsc --noEmit
```

For this docs-only script, a lightweight `git diff` review is enough.

## Demo Steps

### 1. Log In

1. Open the frontend, for example `http://localhost:3001`.
2. If not already authenticated, the app opens the `Sign in` page.
3. Enter the operator email in `Work email`.
4. Enter the password in `Password`.
5. Select `Sign in`.

Expected result:

- The operator reaches the authenticated app.
- The main navigation shows `Patients`, `Audit Readiness`, and `Verify Bundle`.
- If credentials are wrong, the session is expired, or backend auth is unavailable, the login page remains visible with an error.

### 2. Open the Patient Worklist

1. Select `Patients` in the top navigation.
2. Review the `Patient queue` page.

Expected result:

- Patient cards appear when demo data exists.
- Each card summarizes patient workflow posture and links to patient detail.
- If the queue is empty, the page shows an empty state rather than an error.

### 3. Open the Org-Level Audit-Readiness Dashboard

1. Select `Audit Readiness` in the top navigation.
2. Confirm the page title is `Audit readiness`.

Expected result:

- The page shows a `Reviewer workload` summary when available.
- The page shows `Status counts`.
- The page shows `Worklist rows` for latest-per-patient persisted snapshot rows.
- The page is read-only. It should not show approve, reject, assign, export, edit, or create-snapshot controls.

### 4. Read Audit-Readiness Row Fields

In the `Worklist rows` table, review these columns:

- `Patient ID`: clickable link to the patient detail page.
- `Latest Snapshot ID`: the latest persisted review-packet snapshot for that patient.
- `Snapshot Created`: snapshot creation time.
- `Review Status`: current review status such as pending, approved, or rejected.
- `Completion`: audit-readiness posture such as incomplete, review ready, approved not exported, audit ready, or rejected.
- `Review State`: review lifecycle state.
- `Reviewer`: assigned reviewer user ID, or blank marker when unassigned.
- `Next Step`: recommended next audit step and reason.
- `Priority`: normal or high.
- `Bundle Available`: whether an audit bundle can be exported.
- `Exported`: whether an audit bundle export has already been recorded.
- `Formats`: export formats already recorded by the backend.

Expected result:

- Rows give an operator enough context to understand why a patient is or is not audit-ready.
- Status filter chips are available: `All`, `Incomplete`, `Review ready`, `Approved, not exported`, `Audit ready`, and `Rejected`.

### 5. Navigate from Audit Readiness to Patient Detail

1. In the audit-readiness table, select a `Patient ID`.
2. Wait for the patient detail page to load.

Expected result:

- The app opens `/patients/{patient_id}`.
- The page shows patient workflow summary, evidence surfaces, audit status, review-packet backlog, and timeline evidence.

### 6. Review the Patient Audit-Status Panel

1. Find the `ACCESS audit status` section.
2. Review `Review packet readiness`.

Expected fields:

- `Has snapshot`
- `Review state`
- `Review action`
- `Audit bundle available`
- `Audit bundle exported`
- `Export formats`
- `Next step`
- `Completion summary`

Expected result:

- The panel summarizes the latest persisted snapshot audit posture for this patient.
- If audit status cannot load, the page shows `Audit status unavailable`.
- This panel is read-only and should not mutate workflow state.

### 7. Review the Patient Review-Packet Backlog

1. Find the `Review packet backlog` section.
2. Review `Packet drill-in`.

Expected result:

- Summary cards show `Has snapshot`, `Total snapshots`, `Next step`, and `Completion`.
- The backlog table lists recent persisted snapshots with `Created`, `Review status`, `Review state`, `Assigned reviewer`, and `Audit bundle export`.
- If no snapshots exist, the page shows `No review packets yet`.

### 8. Download an Approved Audit Bundle

This step requires an approved snapshot. In the `Audit bundle export` column:

1. If the snapshot is not approved, expect text such as `Unavailable until approved.`
2. If the snapshot is rejected, expect `Unavailable for rejected snapshots.`
3. If the latest approved snapshot is not export-ready, expect `Approved snapshot is not export-ready.`
4. If download actions are available, select each of:
   - `Download JSON`
   - `Download Markdown`
   - `Download PDF`

Expected result:

- Available downloads use the existing approved audit bundle export endpoints.
- Successful downloads may record `audit_bundle_exported` events.
- The JSON bundle contains an `audit_manifest` object.
- The Markdown and PDF downloads provide human-readable audit bundle formats.
- The patient detail page itself does not approve, reject, or assign snapshots in this demo step.

### 9. Copy the Audit Manifest JSON

1. Open the downloaded JSON audit bundle.
2. Find the top-level `audit_manifest` object.
3. Copy only that object, including its opening and closing braces.

The manifest should contain fields like:

```json
{
  "snapshot_id": "<snapshot-id>",
  "patient_id": "<patient-id>",
  "review_status": "approved",
  "generated_from": "persisted_snapshot",
  "packet_json_sha256": "<sha256>",
  "packet_markdown_sha256": "<sha256>",
  "decision_event_count": 1,
  "approval_event_id": "<event-id>",
  "approval_override_used": false
}
```

Expected result:

- The copied JSON is the manifest object, not the full audit bundle.
- The `snapshot_id` matches the snapshot being verified.

### 10. Open the Audit Bundle Verification Page

1. Select `Verify Bundle` in the top navigation.
2. Confirm the page title is `Audit bundle verification`.
3. Find the `Verify manifest` form.

Expected result:

- The page explains that verification compares an exported `audit_manifest` against persisted snapshot data.
- The form has `Snapshot ID`, `Audit manifest JSON`, and `Verify Manifest`.
- The page states that verification is read-only and does not export or update snapshots.

### 11. Verify the Audit Bundle

1. Paste the snapshot ID into `Snapshot ID`.
2. Paste the copied `audit_manifest` object into `Audit manifest JSON`.
3. Select `Verify Manifest`.

Expected result for a valid matching manifest:

- The result says `Verified`.
- The detail text says the snapshot matches the submitted manifest.

Expected result for a valid but mismatched manifest:

- The result says `Mismatch`.
- A table lists each mismatched field with `Field`, `Expected`, and `Actual`.
- This means the submitted manifest does not match the persisted snapshot manifest.

### 12. Interpret Error States

Use these interpretations during the demo:

| State | What the operator sees | Meaning | What to do |
| --- | --- | --- | --- |
| Verified | `Verified` | The submitted manifest matches persisted snapshot data. | Continue demo or record success. |
| Mismatch | `Mismatch` plus field table | The manifest is valid JSON but differs from persisted data. | Confirm the manifest came from the same snapshot and was not edited. |
| Invalid JSON | `Invalid manifest: Invalid manifest JSON...` | The pasted manifest is not parseable JSON. | Recopy the `audit_manifest` object from the JSON bundle. |
| Missing snapshot ID | `Invalid manifest: Enter a snapshot ID.` | The form was submitted without a snapshot ID. | Paste the snapshot ID and retry. |
| Missing field or invalid manifest shape | `Request error` with backend validation detail, or a local invalid-manifest message | Required manifest fields are missing or the object shape does not match the backend contract. | Recopy the full `audit_manifest` object. |
| Auth error | `Request error` or redirect to sign in | The session is missing or expired. | Sign in again, then retry verification. |
| Backend error | `Request error` with a safe message such as snapshot not found or verification failed | Backend rejected the request or is unavailable. | Check the snapshot ID, backend health, and tenant/demo data. |

## Troubleshooting

- If `/login` does not load, confirm the frontend is running at the URL you opened.
- If login shows `Unable to sign in right now. Please try again.`, confirm the backend is running and the frontend API base URL points to it.
- If authenticated pages redirect to login, sign in again and confirm cookies are enabled.
- If `Audit Readiness` shows `Unable to load audit readiness`, check backend health and `NEXT_PUBLIC_API_BASE_URL`.
- If no audit-readiness rows appear, the local database may not have persisted review-packet snapshots.
- If bundle download links are absent, the selected patient may not have an approved export-ready snapshot.
- If JSON verification fails with invalid JSON, make sure you copied only the `audit_manifest` object, not the full audit bundle.
- If verification reports mismatch, confirm the snapshot ID and manifest come from the same exported bundle.
- If `localhost:3000` looks stale, use the established demo helper and open `http://localhost:3001`.

## Demo Success Criteria

The demo is successful when an operator can:

1. Sign in.
2. Open `Patients`.
3. Open `Audit Readiness`.
4. Explain a patient row using the visible audit-readiness fields.
5. Open patient detail from the audit-readiness row.
6. Explain the patient audit-status panel.
7. Explain the review-packet backlog.
8. Download JSON, Markdown, and PDF audit bundles for an approved snapshot where available.
9. Copy `audit_manifest` from the JSON bundle.
10. Open `Verify Bundle`.
11. Verify the manifest successfully or correctly interpret mismatch/error states.
12. Confirm no unintended approve, reject, assign, edit, create-snapshot, or broad admin behavior was introduced by this demo path.

## Follow-Up Notes Template

```text
Date:
Reviewer:
Frontend URL:
Backend URL:
Login account:
Patient ID:
Snapshot ID:

Audit-readiness row status:
Patient audit-status result:
Review-packet backlog result:
Downloads attempted:
- JSON:
- Markdown:
- PDF:

Verification result:
Errors observed:
Demo passed?:
Follow-up items:
```
