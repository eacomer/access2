# ACCESS2 V2 Local Demo Operator Script

## Purpose

Use this one-page script for a live localhost-only ACCESS2 V2 correction-loop demo.

The demo shows reviewer assignment, rejection, corrected evidence, new snapshot creation, corrected approval, audit bundle readiness, and immutable snapshot history. It is a presenter script, not the full technical handoff.

## Safety Scope

- Frontend target must be loopback only: `http://localhost:3000` or a verified current-workspace `http://localhost:3001`.
- API target must be `http://localhost:8000/api/v1`.
- Do not use Railway, staging, `salvardata.com`, `api.salvardata.com`, `railway.app`, `up.railway.app`, `https://`, or any non-loopback host.
- Use only synthetic local demo data.
- Do not use real PHI.

## Preflight Checklist

- Confirm repo state is known and clean enough for a demo.
- Confirm backend health:
  - `http://localhost:8000/api/v1/health/live`
  - `http://localhost:8000/api/v1/health/ready`
- Confirm frontend `/login` returns 200 on the selected loopback port.
- Confirm explicit local E2E variables if running the automated rehearsal:
  - `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true`
  - `ACCESS2_E2E_BASE_URL=http://localhost:3000` or verified `http://localhost:3001`
  - `ACCESS2_E2E_API_BASE_URL=http://localhost:8000/api/v1`
  - `ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID=<disposable-local-patient-id>`
- Run seed/reset only if needed, only locally, and only with `ACCESS2_ENABLE_LOCAL_MUTATION_E2E=true`.

## Demo Opening Talk Track

ACCESS2 proves that a patient need moved through signal, escalation, intervention, outcome, care update, resolution, evidence, immutable review, and audit bundle readiness.

V2 adds a local reviewer correction loop. A reviewer can assign a packet, reject it with a reason, preserve the rejected packet as immutable history, create a new packet from corrected current evidence, and approve the corrected packet when the persisted checklist is complete.

## Live Demo Sequence

1. Open the local frontend on the verified loopback URL.
2. Log in to the local demo environment.
3. Navigate to the disposable local demo patient.
4. Show the current review packet posture in the patient review-packet backlog.
5. Assign the latest `pending_review` snapshot to the reviewer.
6. Reject the latest pending snapshot with a demo-safe reason.
7. Show that the rejected snapshot is terminal, read-only, and not audit-bundle-ready.
8. Create a corrected/new review packet snapshot from current corrected evidence.
9. Approve the corrected latest `pending_review` snapshot.
10. Show the latest snapshot is `approved` and audit bundle availability is true.
11. Show the prior rejected snapshot still appears in backlog/history and was not edited or overwritten.

## Key Phrases To Say

- "The reviewer is not editing the old snapshot; they are making a decision on an immutable packet."
- "A rejection does not overwrite the evidence trail."
- "The correction creates a new packet from the current corrected case state."
- "The prior rejected snapshot remains part of the audit history."
- "Approval is only allowed when the persisted checklist has no missing evidence."
- "This is local-only today; production V1 remains read-only."

## Fallback Script

- If local Next.js cold route compilation causes delays: "The local dev server is compiling routes. The workflow is still localhost-only; we can pause here or use the already recorded local E2E result."
- If port `3000` is stale: "We are switching only to a verified current-workspace loopback frontend on `3001`. The API remains `http://localhost:8000/api/v1`."
- If Playwright hits `spawn EPERM` or leaves generated artifacts: "This is a local browser/process issue. It does not change the product proof. We will rerun only against loopback and clean generated artifacts before handoff."
- If the local E2E is not run live: "The latest recorded localhost rehearsal passed with `1 passed (10.6m)` and verified assignment, rejection, corrected snapshot creation, approval, read-only terminal snapshots, and preserved rejected history."

## Do Not Say Or Do

- Do not say production mutation is enabled.
- Do not imply staging mutation testing is approved.
- Do not imply EHR, FHIR, billing, AI recommendations, or real CMS submission integration exists.
- Do not use real PHI.
- Do not run mutation tests against production, Railway, staging, `https://`, or any non-loopback host.
- Do not describe rejected snapshots as edited, refreshed, repaired, or overwritten.

## Close

ACCESS2 can show the correction loop while preserving immutable audit history: the rejected packet remains as evidence, the corrected current case state creates a new packet, and the approved latest packet is ready for audit bundle export.
