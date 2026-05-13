# ACCESS2 V2 Correction Loop Demo

## Purpose

Use this script to demonstrate the local-only ACCESS2 V2 correction loop:

```text
latest rejected snapshot -> corrected synthetic outcome/evidence -> create new immutable review packet snapshot -> new latest pending_review snapshot -> old rejected packet remains preserved/read-only
```

This demo shows how ACCESS2 handles reviewer correction without changing an old packet. A rejected packet stays historical audit evidence. Corrected evidence/current state creates a new immutable review packet snapshot.

## Local-Only Warning

Run this only against a disposable local ACCESS2 environment.

Do not run this script, seed, or mutation E2E against:

- `https://access2.salvardata.com`
- `https://api.salvardata.com/api/v1`
- Railway production or Railway-like shared demo hosts
- Any environment containing real PHI

Production E2E remains read-only. Demo Patient 3 remains the production read-only rejected-posture scenario, not a repeatable mutation target.

## What The Demo Proves

- Reviewer rejection can move the latest immutable snapshot to a rejected posture with required reason/evidence.
- The rejected snapshot keeps its persisted packet JSON and Markdown.
- Audit bundle export remains blocked for rejected snapshots.
- The disposable local scenario can add post-rejection synthetic correction evidence before the next snapshot is created.
- The corrected evidence marker is a later `systolic_bp` outcome with source `access2_local_v2_post_rejection_correction`, value `124`, and care-update summary `Post-rejection corrected evidence: synthetic systolic BP outcome improved after the completed intervention.`
- ACCESS2 creates a new immutable review packet snapshot from current evidence after the rejected posture.
- The new latest snapshot becomes `pending_review`.
- Assignment and rejection controls appear only for the new latest `pending_review` snapshot.
- Historical rejected/approved snapshots remain visible and read-only.
- The ACCESS proof chain is preserved: signal -> escalation -> intervention -> outcome -> evidence -> case summary -> immutable review packet snapshot -> assignment/rejection -> new immutable snapshot from corrected evidence.

## Prerequisites

- Repo root: `C:\dev\access2`
- Backend is running locally and healthy at `http://localhost:8000/api/v1`.
- Frontend is running locally, preferably a clean current-workspace instance on `http://localhost:3001`.
- `frontend/.env.local` points at the local backend API:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

- Local demo credentials exist:

```text
admin@example.com / Admin123!
```

- Generated artifacts remain uncommitted:

```text
frontend/.next
frontend/playwright-report
frontend/test-results
frontend/next-env.d.ts
```

## Backend And Frontend Startup Assumptions

Verify backend health:

```powershell
cd C:\dev\access2
Invoke-RestMethod http://localhost:8000/api/v1/health/live
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
```

Start a clean frontend. The documented helper typically uses port 3001:

```powershell
cd C:\dev\access2
.\scripts\start-access2-demo-frontend.ps1
```

If port 3000 is serving stale code or stale `.next` output, do not use it for this demo. Use a clean localhost port such as `http://localhost:3001`.

## Seed Or Reset Disposable Local State

Run the local-only seed/reset from the backend directory:

```powershell
cd C:\dev\access2\backend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:PYTHONPATH="C:\dev\access2\backend"
py -3 -m scripts.seed_local_v2_rejection_mutation
```

Expected output includes:

```text
ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID=<patient-id>
```

This seed creates or repairs one synthetic local disposable patient with marker:

```text
access2-local-v2-mutation:reviewer-rejection
```

If the previous latest snapshot was rejected, the seed first adds synthetic post-rejection correction evidence, then creates a new latest `pending_review` snapshot from that current evidence. It does not rewrite the rejected terminal snapshot.

## Local E2E Command

Run only against localhost:

```powershell
cd C:\dev\access2\frontend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:ACCESS2_E2E_BASE_URL="http://localhost:3001"
$env:ACCESS2_E2E_ADMIN_EMAIL="admin@example.com"
$env:ACCESS2_E2E_ADMIN_PASSWORD="Admin123!"
$env:ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID="<value printed by seed script>"
& "C:\Program Files\nodejs\npm.cmd" run test:e2e:local-mutation
```

Latest validated result:

```text
1 passed (2.2m)
```

That run used a clean frontend at `http://localhost:3001` after stale port-3000/node process friction. The current local mutation spec also creates the same synthetic correction evidence after reviewer rejection and before selecting `Create new review packet snapshot`, so the new packet captures an improved outcome posture while the old rejected packet remains unchanged.

## Manual Demo Walkthrough

### 1. Sign In

Open the local frontend and sign in:

```text
http://localhost:3001/login
```

Expected result:

- Authenticated navigation appears.
- `Patients`, `Reviewer Queue`, and `Verify Bundle` are visible.

### 2. Open The Disposable Patient

Open the patient printed by the seed:

```text
http://localhost:3001/patients/<ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID>
```

Expected result:

- Patient detail renders.
- `Review packet backlog` / `Packet drill-in` is visible.
- Latest snapshot starts as `Pending Review` after seed/reset.

### 3. Reject The Latest Pending Snapshot

In the `Packet drill-in` backlog:

1. Confirm `Assign reviewer` appears only on the latest `Pending Review` snapshot.
2. Assign the current reviewer user ID when demonstrating assignment.
3. Confirm success copy: `Reviewer assigned.`
4. Confirm `Reject snapshot` appears only on the latest `Pending Review` snapshot.
5. Enter a non-empty rejection reason.
6. Select `Reject snapshot`.

Expected result:

- Latest review posture becomes `Rejected`.
- Assignment/rejection controls disappear from the rejected latest snapshot.
- Audit bundle export says `Unavailable for rejected snapshots.`
- The snapshot row shows `Read-only for this snapshot.`

### 4. Verify The Rejected Packet Is Preserved

Stay in `Packet drill-in`.

Expected observations:

- The rejected snapshot remains visible in the backlog.
- The rejected row remains read-only.
- Existing packet JSON and Markdown are not changed or rebuilt.
- The rejected snapshot blocks audit bundle export and manifest verification.

### 5. Create A New Immutable Review Packet Snapshot

When the latest posture is rejected, the patient detail page should expose:

```text
Create new review packet snapshot
```

Select it.

Expected result:

- Success copy appears: `New review packet snapshot created.`
- A new latest snapshot appears with `Pending Review`.
- The older rejected snapshot remains visible and read-only.
- The new snapshot is generated from current evidence. In the local E2E proof, that current evidence includes the post-rejection correction marker and an improved systolic BP outcome trend.
- This is creation from current evidence while the rejected packet stays preserved.

### 6. Verify Latest-Only Controls

After the new snapshot is latest `Pending Review`:

- `Assign reviewer` appears for the new latest snapshot.
- `Reject snapshot` appears for the new latest snapshot.
- The old rejected snapshot still shows `Read-only for this snapshot.`
- No create-snapshot button remains while the latest snapshot is `pending_review`.

### 7. Check Reviewer Work Queue Posture

Open:

```text
http://localhost:3001/audit-readiness
```

Expected result:

- Reviewer Work Queue remains read-only.
- No approve, reject, assign, override, export, or create-snapshot mutation controls are present.

## Expected Audit/Evidence Story

Use this talk track:

ACCESS2 does not overwrite review evidence when a reviewer rejects a packet. The rejected packet remains a historical immutable audit artifact, including the packet JSON, packet Markdown, review state, reviewer assignment, rejection reason, and audit events. When evidence or outcomes are corrected, ACCESS2 creates a new immutable review packet snapshot from the current evidence. In the local synthetic scenario, the corrected current evidence is visible as a post-rejection care update and an improved `systolic_bp` outcome trend. Review controls apply to the new latest pending snapshot only, while old rejected/approved packets stay available as audit history.

This supports the ACCESS proof chain because the system can show:

- why the patient needed action
- what intervention occurred
- what measurable outcome followed
- what evidence supported review
- which packet was rejected and why
- which new packet was created from corrected/current evidence
- that historical packets were preserved unchanged

## What Not To Do In Production

- Do not run `scripts.seed_local_v2_rejection_mutation` against production.
- Do not run `npm run test:e2e:local-mutation` against production.
- Do not use Demo Patient 3 for repeatable mutation validation.
- Do not mutate shared production demo data.
- Do not change Railway config.
- Do not change the backend startup command; it remains `bash scripts/render-start.sh`.
- Do not add superuser override approval or broad workflow mutation controls as part of this demo.

## Troubleshooting

### Stale `.next` Cache

Symptom:

```text
Cannot find module './570.js'
```

Fix:

1. Stop the stale frontend dev server if possible.
2. Delete `frontend\.next`.
3. Restart the frontend.
4. Reopen `/login`.

### Port 3000 Held By Stale Node Processes

If Windows will not stop stale node processes on port 3000, start a clean current-workspace frontend on another localhost port such as 3001 and set:

```powershell
$env:ACCESS2_E2E_BASE_URL="http://localhost:3001"
```

The local mutation spec still refuses production/Railway-like hosts.

### Seed Starts From The Wrong Snapshot State

Rerun:

```powershell
cd C:\dev\access2\backend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:PYTHONPATH="C:\dev\access2\backend"
py -3 -m scripts.seed_local_v2_rejection_mutation
```

Expected result:

- The latest snapshot is restored to `pending_review` by creating a new immutable snapshot when needed.
- Old rejected snapshots remain preserved.

### Playwright Chromium `spawn EPERM`

This can be local Windows permission noise. Rerun the local-only Playwright command with the approved execution path for this environment.

## Stop Conditions

Stop and investigate before changing product code if:

- Backend health fails.
- Frontend `.env.local` points to production.
- The local mutation spec tries to target production/Railway-like hosts.
- Rejected snapshots lose persisted packet content.
- Historical rejected/approved snapshots disappear from the backlog.
- Reviewer Work Queue exposes mutation controls.
- Generated artifacts appear in `git status --short`.
