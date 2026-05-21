# ACCESS2 V2 Correction Loop Demo Script

## Demo Purpose

Use this operator script to demonstrate the completed local-only ACCESS2 V2 correction loop:

```text
assignment -> rejection with reason -> immutable rejected packet -> corrected evidence -> new immutable pending snapshot -> approval -> terminal read-only history
```

The demo shows how ACCESS2 proves correction, review, and immutable audit history without overwriting prior evidence. A rejected packet remains a historical audit artifact. Corrected current evidence is captured by creating a new immutable review packet snapshot, and approval applies only to the corrected latest packet.

This is localhost-only V2 mutation behavior. Production remains V1 read-only and synthetic/demo-only.

## Audience And Duration

- Audience: operator, product, demo, or implementation-review walkthrough.
- Target duration: 5-10 minutes.
- Goal: explain the correction-loop proof chain clearly, not run broad validation.

## Local-Only Warning

Run this only against a disposable local ACCESS2 environment.

Do not run this script, seed/reset, or mutation E2E against:

- `https://access2.salvardata.com`
- `https://api.salvardata.com/api/v1`
- Railway production or Railway-like shared demo hosts
- Any environment containing real PHI

Production E2E remains read-only. Demo Patient 3 remains the production read-only rejected-posture scenario, not a repeatable mutation target.

## Prerequisites

- Repo root is `C:\dev\access2`.
- Backend is running locally and healthy at `http://localhost:8000/api/v1`.
- Frontend is running locally, preferably a clean current-workspace instance on `http://localhost:3001`.
- `frontend/.env.local` points at the local backend API:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

- Safe localhost-only mutation env vars are set only in the shells used for seed/reset or E2E.
- Local demo credentials exist:

```text
admin@example.com / Admin123!
```

- No production mutation testing.
- No real PHI.
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

This invokes:

```text
backend/scripts/seed_local_v2_rejection_mutation.py
```

Expected output includes:

```text
ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID=<patient-id>
```

The seed creates or repairs one synthetic local disposable patient with marker:

```text
access2-local-v2-mutation:reviewer-rejection
```

The script requires:

```text
ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true
```

If the previous latest snapshot was rejected, the seed adds synthetic post-rejection correction evidence, then creates a new latest `pending_review` snapshot from that current evidence. It does not rewrite the rejected terminal snapshot.

This is not a Railway seed command, not a production seed command, and not a backend startup command.

## Local E2E Command

Run only against localhost:

```powershell
cd C:\dev\access2\frontend
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:ACCESS2_E2E_BASE_URL="http://localhost:3001"
$env:ACCESS2_E2E_API_BASE_URL="http://localhost:8000/api/v1"
$env:ACCESS2_E2E_ADMIN_EMAIL="admin@example.com"
$env:ACCESS2_E2E_ADMIN_PASSWORD="Admin123!"
$env:ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID="<value printed by seed script>"
& "C:\Program Files\nodejs\npm.cmd" run test:e2e:local-mutation
```

If the current clean frontend is on `http://localhost:3000` instead of `http://localhost:3001`, use `http://localhost:3000` for `ACCESS2_E2E_BASE_URL` only after confirming it is the current workspace and not a stale `.next` instance. Keep `ACCESS2_E2E_API_BASE_URL` pointed at the local backend API.

Before a timed rehearsal, warm the local dev routes in a browser or with a local-only smoke visit to `/login`, the seeded patient detail URL, and `/audit-readiness`. Cold Next.js route compilation can otherwise consume the Playwright timeout even when the workflow itself is healthy.

Latest known local result:

```text
May 16, 2026: 1 passed (10.6m), localhost only, using http://localhost:3000 and http://localhost:8000/api/v1
```

The local E2E proves the scripted path, including assignment, rejection, correction evidence, new snapshot creation, corrected approval, terminal read-only posture, and read-only Reviewer Work Queue posture. Manual demo observations still matter because the demo is meant to explain why the proof chain is defensible.

The May 16, 2026 rehearsal needed local seed/reset and local troubleshooting only. The first non-elevated Playwright run hit Chromium `spawn EPERM`, partial warmed runs exposed slow Docker-backed Next.js route compilation, and the local frontend on port `3000` needed stale `.next` output cleared before the successful run. No production, staging, Railway, `salvardata.com`, or non-loopback mutation target was used.

## Manual Walkthrough Script

### 1. Sign In Locally

Open:

```text
http://localhost:3001/login
```

Say:

```text
We are signed into a local disposable ACCESS2 V2 environment. This is not production, and no real PHI is used.
```

Expected observation:

- Authenticated navigation appears.
- `Patients`, `Reviewer Queue`, and `Verify Bundle` are visible.

### 2. Open The Seeded Synthetic Patient

Open the patient printed by the seed:

```text
http://localhost:3001/patients/<ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID>
```

Say:

```text
This patient is the disposable synthetic V2 correction-loop case. The local marker is access2-local-v2-mutation:reviewer-rejection.
```

Expected observation:

- Patient detail renders.
- `Review packet backlog` / `Packet drill-in` is visible.
- The latest snapshot starts as `Pending Review` after seed/reset.
- Outcome Evidence Readiness is read-only. When latest persisted packet evidence is available, it shows ACCESS track evidence such as eCKM hypertension, systolic BP baseline/follow-up, readiness status, evidence completeness, and care update milestone.

### 3. Identify The Latest Actionable Packet

In the `Packet drill-in` backlog, locate the latest `Pending Review` snapshot.

Say:

```text
Only the latest pending-review packet is actionable. Older packets and terminal packets are audit history and stay read-only.
```

Expected observation:

- Assignment and rejection controls are scoped to the latest `Pending Review` snapshot.
- Historical rows do not expose mutation controls.

### 4. Assign The Pending Packet

Use the assignment control on the latest pending packet.

Say:

```text
Assignment records reviewer accountability for this packet without changing the packet JSON or Markdown.
```

Expected observation:

- Success copy appears: `Reviewer assigned.`
- The snapshot remains `Pending Review`.
- Persisted packet content remains unchanged.

### 5. Reject The Original Packet With A Reason

Use `Reject snapshot` on the same latest pending packet. First point out that a non-empty reason is required, then enter a demo-safe reason such as:

```text
Synthetic local V2 rejection mutation test reason: outcome evidence needs correction.
```

Say:

```text
The reviewer is rejecting this packet because the outcome evidence needs correction. ACCESS2 records who rejected it, when it happened, and the reason.
```

Expected observation:

- Latest review posture becomes `Rejected`.
- Assignment and rejection controls disappear from the rejected snapshot.
- Audit bundle export says `Unavailable for rejected snapshots.`
- The rejected row shows `Read-only for this snapshot.`

### 6. Explain The Immutable Rejected Packet

Stay in the backlog and point to the rejected row.

Say:

```text
The rejected packet is not repaired in place. Its packet_json and packet_markdown stay preserved as historical audit evidence.
```

Expected observation:

- The rejected snapshot remains visible in the backlog.
- The rejected row remains read-only.
- Existing packet JSON and Markdown are not changed or rebuilt.
- Rejected posture blocks audit bundle generation and manifest verification.

### 7. Create A New Snapshot From Corrected Evidence

When the latest posture is rejected, the patient detail page should expose:

```text
Create new review packet snapshot
```

Select it.

Say:

```text
Corrected current evidence is represented by creating a new immutable snapshot. ACCESS2 does not overwrite the rejected packet.
```

Expected observation:

- Success copy appears: `New review packet snapshot created.`
- A new latest snapshot appears with `Pending Review`.
- The older rejected snapshot remains visible and read-only.
- The new snapshot is generated from current evidence.
- In the local proof, current evidence includes the post-rejection correction marker, a `systolic_bp` outcome value of `124`, source `access2_local_v2_post_rejection_correction`, and an improved outcome trend.
- Outcome Evidence Readiness can show the synthetic ACCESS track story from the persisted packet: clinical track and condition, metric, baseline measure, follow-up measure, outcome readiness such as `control_achieved` or `minimum_improvement_achieved`, completeness, and the care update milestone.

### 8. Approve The Corrected Latest Pending Packet

Use `Approve snapshot` on the corrected latest `Pending Review` snapshot.

Say:

```text
Approval applies only to the corrected latest packet, and only when the persisted review checklist has no missing evidence.
```

Expected observation:

- Success copy appears: `Review packet snapshot approved.`
- Latest review posture becomes `Approved`.
- Audit bundle availability becomes true for the approved snapshot.
- Assignment, rejection, approval, and create-snapshot controls disappear.
- The old rejected snapshot remains visible and read-only.
- The approved snapshot row shows `Read-only for this snapshot.`

### 9. Confirm Historical Snapshot Posture

Point to both terminal rows.

Say:

```text
The rejected packet and the approved corrected packet are both terminal records. They remain available as audit history, and neither exposes mutation controls.
```

Expected observation:

- Historical rejected snapshots expose no mutation controls.
- Historical approved snapshots expose no mutation controls.
- At least two rows can show `Read-only for this snapshot.`

### 10. Confirm Reviewer Work Queue Remains Read-Only

Open:

```text
http://localhost:3001/audit-readiness
```

Say:

```text
The Reviewer Work Queue remains read-only. V2 mutation controls are patient-detail-only in this local proof.
```

Expected observation:

- Reviewer Work Queue remains read-only.
- No approve, reject, assign, override, export, or create-snapshot mutation controls are present.

## Expected UI Observations

- Assignment control appears only for the latest `pending_review` snapshot.
- Rejection control appears only for the latest `pending_review` snapshot.
- Create new snapshot control appears only in the local gated context after rejected or no-snapshot posture.
- Approval control appears only for the latest `pending_review` snapshot when the persisted review checklist has `missing_count == 0`.
- Terminal approved snapshots expose no mutation controls.
- Terminal rejected snapshots expose no mutation controls.
- Historical snapshots expose no mutation controls.
- Reviewer Work Queue remains read-only.

## Audit/Evidence Talk Track

Use this proof-chain language:

```text
signal -> escalation -> intervention -> outcome -> care update -> evidence -> case summary -> immutable review packet snapshot -> assignment -> rejection -> corrected evidence -> new immutable review packet snapshot -> approval -> audit bundle/manifest expectations
```

ACCESS2 does not overwrite review evidence when a reviewer rejects a packet. The rejected packet remains a historical immutable audit artifact, including packet JSON, packet Markdown, review state, reviewer assignment, rejection reason, and audit events.

When evidence or outcomes are corrected, ACCESS2 creates a new immutable review packet snapshot from current evidence. In the local synthetic scenario, the corrected current evidence is visible as a post-rejection care update and an improved `systolic_bp` outcome trend. Review controls apply to the new latest pending snapshot only, while old rejected and approved packets stay available as audit history.

Outcome Evidence Readiness is the presenter bridge between clinical facts and review posture. Say:

```text
This is not a claim submission or CMS submission. This is the evidence-readiness layer that helps a provider prove whether the outcome story is complete enough for review.
```

For the local synthetic patient, point out the ACCESS track, metric, baseline, follow-up, outcome readiness status, evidence completeness, and care update milestone. The section supports the ACCESS2 chain from signal to intervention to measurable outcome to care update to immutable review packet to audit-ready evidence; it is not CMS production submission, claims submission, billing automation, or a production mutation workflow.

This supports the ACCESS proof chain because the system can show:

- why the patient needed action
- what intervention occurred
- what measurable outcome followed
- which ACCESS track outcome evidence was ready or missing
- which care update milestone supported review
- what evidence supported review
- which packet was assigned
- which packet was rejected and why
- which new packet was created from corrected/current evidence
- which corrected packet was approved after measurable outcome improvement
- that historical packets were preserved unchanged

## Production Do Nots

- Do not run mutation E2E against `https://access2.salvardata.com`.
- Do not run mutation E2E against `https://api.salvardata.com/api/v1`.
- Do not run `scripts.seed_local_v2_rejection_mutation` against production.
- Do not use Demo Patient 3 for repeatable mutation validation.
- Do not mutate shared production demo data.
- Do not use Railway startup commands for seed/reset.
- Do not change Railway config.
- Do not change the backend startup command; it remains `bash scripts/render-start.sh`.
- Do not enable staging mutation until isolated staging is provisioned and approved.
- Do not add superuser override approval or broad workflow mutation controls as part of this demo.

## Troubleshooting

### `frontend/.env.local` Backend URL Mismatch

Symptom:

```text
Unable to sign in right now. Please try again.
```

Check:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Then confirm backend health before changing product code.

### Stale `.next` Cache

Symptom:

```text
Cannot find module './570.js'
```

or an `ENOENT` for a compiled page such as `.next/server/app/login/page.js`.

Fix:

1. Stop the stale frontend dev server if possible.
2. Delete `frontend\.next`.
3. Restart the frontend.
4. Reopen `/login`.

### Frontend Port Mismatch

If port 3000 is held by stale node processes, start a clean current-workspace frontend on another localhost port such as 3001 and set:

```powershell
$env:ACCESS2_E2E_BASE_URL="http://localhost:3001"
```

The local mutation spec still refuses production/Railway-like hosts.

### Playwright Chromium `spawn EPERM`

This can be local Windows permission noise. Rerun the local-only Playwright command with the approved execution path for this environment. Do not switch the target to production to work around a local browser issue.

### Missing Safe Localhost Env Vars

If the seed fails, confirm:

```powershell
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:PYTHONPATH="C:\dev\access2\backend"
```

If the local E2E is skipped, confirm:

```powershell
$env:ACCESS2_ENABLE_LOCAL_MUTATION_E2E="true"
$env:ACCESS2_E2E_BASE_URL="http://localhost:3001"
$env:ACCESS2_E2E_API_BASE_URL="http://localhost:8000/api/v1"
$env:ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID="<value printed by seed script>"
```

The local E2E intentionally skips when `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true` is not set.

### Cold Local Next.js Route Compilation

Symptom:

```text
The local mutation E2E reaches assignment, rejection, corrected evidence, or new snapshot creation, then exceeds the Playwright timeout before approval assertions.
```

Check:

- The frontend target is loopback-only, such as `http://localhost:3000` or `http://localhost:3001`.
- `ACCESS2_E2E_API_BASE_URL` is explicitly set to `http://localhost:8000/api/v1`.
- The seeded patient detail route and `/audit-readiness` have been opened once after the dev server starts.

Then rerun only the localhost-gated command. Do not switch to production, Railway, or staging targets to work around local route compilation latency.

### Production-Like URL Blocked By Host Guard

The seed and local mutation E2E must fail closed when configured target values contain production or Railway-like hosts such as:

```text
access2.salvardata.com
api.salvardata.com
railway.app
up.railway.app
```

This is expected safety behavior. Do not bypass it.

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

## Stop Conditions

Stop and investigate before changing product code if:

- Backend health fails.
- `frontend/.env.local` points to production.
- The local mutation spec tries to target production/Railway-like hosts.
- Rejected snapshots lose persisted packet content.
- Historical rejected or approved snapshots disappear from the backlog.
- Reviewer Work Queue exposes mutation controls.
- Generated artifacts appear in `git status --short`.
- Any real PHI appears.

## Definition Of Done

- Operator can complete or explain the local correction loop in 5-10 minutes.
- Script includes prerequisites, seed/reset, E2E command, manual walkthrough, UI observations, audit talk track, production do nots, and troubleshooting.
- Script contains no secrets, no real PHI, and no production mutation guidance.
- Production remains read-only.

## Recommended Next Slice

After this demo polish, the recommended next non-staging product workflow slice is Candidate B from [access2-v2-product-workflow-next-slice.md](C:/dev/access2/docs/access2-v2-product-workflow-next-slice.md): patient-detail correction-loop status messaging.

That would be a future product frontend slice. It is not part of this docs-only demo polish.
