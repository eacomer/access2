# ACCESS2 V1 Demo-Day Operator Script

## Purpose

Use this script to present the production ACCESS2 V1 demo to stakeholders. The demo shows how ACCESS2 proves that chronic-care interventions led to measurable outcomes and audit-ready evidence.

Core evidence chain:

```text
signal → escalation → intervention → outcome → evidence → case summary → immutable review packet snapshot → approval/rejection → audit bundle → manifest verification
```

This script is read-only. Do not create real patients, enter real PHI, approve, reject, override, assign, export, or change workflow state during the stakeholder walkthrough.

## Production Access

- Frontend: https://access2.salvardata.com
- Backend API: https://api.salvardata.com/api/v1
- Login: `admin@example.com` / `Admin123!`
- Data posture: synthetic/demo data only; no real PHI.

## Demo Flow

1. Open the production frontend and sign in.
2. Open `Demo Guide` at `/demo-guide`.
3. Open `Release Summary` at `/demo/release-summary`.
4. Open `Reviewer Queue` at `/audit-readiness`.
5. Walk the four seeded synthetic demo patients:
   - Demo Patient 1 - Audit Ready: `f4c31931-8fc2-41d6-9f45-9ab0bd039088`
   - Demo Patient 2 - Missing Evidence: `1c5c7db8-96f8-47af-a643-741641ecdcf3`
   - Demo Patient 3 - Rejected Review: `4c1ef5ef-1216-453d-b317-b965a0dd1dea`
   - Demo Patient 4 - Override Approval: `2e9dc25c-2e56-4d6a-aea0-8706d33b0444`
6. For Demo Patient 1, show audit bundle download posture and manifest verification at `/audit-bundle-verify`.

## Page Walkthrough

### Demo Guide

Show that the guide frames the ACCESS2 evidence story and confirms the demo uses synthetic data. Use this page to set expectations: ACCESS2 V1 is about audit evidence, not broad platform scope.

### Demo Release Summary

Show the Evidence Proof Checklist. Point out that it covers all four synthetic patients and makes the signal-to-manifest-verification chain explicit.

What to say:

- Demo Patient 1 proves the complete audit-ready path.
- Demo Patient 2 proves ACCESS2 can identify missing evidence before audit readiness.
- Demo Patient 3 proves a rejected review posture is visible and blocks audit readiness.
- Demo Patient 4 proves override-approved posture is visible without exposing override controls.

What not to expect:

- No approve, reject, override, assign, export, or create-snapshot controls appear on this read-only summary.

### Reviewer Work Queue

Open `/audit-readiness`. Show lifecycle counts, read-only queue rows, patient-detail links, next-step text, review state, and export state.

What to say:

- The queue helps reviewers find audit-ready, missing-evidence, rejected, override-approved, pending, and exported bundle states.
- It is a review posture and navigation surface in V1, not a mutation workflow.

What not to click or expect:

- Do not look for approve, reject, override, assign, export, or create-snapshot actions here.

## Patient Walkthroughs

### Demo Patient 1 - Audit Ready

Open the patient detail page for `f4c31931-8fc2-41d6-9f45-9ab0bd039088`.

Show:

- Evidence Chain panel.
- Manifest Verification panel.
- Outcome Proof Gaps panel.
- Review packet backlog and approved/export-ready audit bundle posture.
- JSON, Markdown, and PDF audit bundle download availability when shown.

Evidence story:

- This patient demonstrates the complete path from signal to outcome proof, approved immutable snapshot, audit bundle availability, and manifest verification.

Do not:

- Use this page to create a new snapshot or change approval state.

### Demo Patient 2 - Missing Evidence

Open the patient detail page for `1c5c7db8-96f8-47af-a643-741641ecdcf3`.

Show:

- Outcome Proof Gaps and readiness reasons.
- Missing or incomplete outcome/evidence proof.
- Next-step explanation.

Evidence story:

- ACCESS2 does not treat workflow activity alone as audit-ready. The system must prove a measurable outcome with supporting evidence.

Do not:

- Add evidence live or try to force audit readiness during the demo.

### Demo Patient 3 - Rejected Review

Open the patient detail page for `4c1ef5ef-1216-453d-b317-b965a0dd1dea`.

Show:

- Existing proof packet/snapshot posture.
- Rejected review state.
- Blocked export/readiness posture.

Evidence story:

- ACCESS2 preserves reviewer decision state and shows that rejected review blocks audit readiness.

Do not:

- Expect a reviewer rejection button in V1. Rejection through UI is intentionally skipped in production E2E.

### Demo Patient 4 - Override Approval

Open the patient detail page for `2e9dc25c-2e56-4d6a-aea0-8706d33b0444`.

Show:

- Override-approved review posture.
- Evidence panels and manifest verification posture.
- Read-only override explanation.

Evidence story:

- ACCESS2 can surface override-approved evidence state while preserving a read-only frontend demo posture.

Do not:

- Expect a superuser override approval button in V1. Override approval through UI is intentionally skipped in production E2E.

## Audit Bundle And Manifest Verification

Use Demo Patient 1 when an approved/export-ready bundle is visible.

1. Download the JSON audit bundle.
2. Show that JSON includes persisted readiness reasons.
3. Download Markdown and PDF if time allows.
4. Copy the JSON `audit_manifest` object.
5. Open `/audit-bundle-verify`.
6. Paste the snapshot ID and manifest JSON.
7. Verify the manifest.

What to say:

- Audit bundles use persisted snapshot, evidence, and event metadata.
- Verification compares the submitted manifest against persisted snapshot data.
- Manifest verification is read-only and does not submit to CMS.

## Talk Track

- ACCESS2 proves the chain from signal to measurable outcome to audit evidence.
- Immutable review packet snapshots preserve what was reviewed.
- Readiness reasons explain why a case is audit-ready, missing evidence, rejected, or override-approved.
- Audit bundles are generated from persisted evidence, not rebuilt from changing live views.
- Manifests verify exported bundles against persisted snapshot data.
- The Reviewer Work Queue is read-only in V1 and helps operators navigate proof posture safely.

## Expected Skipped Tests

Production E2E baseline:

```text
8 passed, 2 skipped, 0 failed
```

The two skipped tests are intentional V1 read-only constraints:

- Demo Patient 3 reviewer rejection through UI.
- Demo Patient 4 superuser override approval through UI.

Reason: ACCESS2 V1 does not expose reviewer rejection or superuser override approval mutation controls in the frontend.

## Demo Failure Fallback

1. Check backend health:

   ```powershell
   Invoke-RestMethod "https://api.salvardata.com/api/v1/health/live"
   Invoke-RestMethod "https://api.salvardata.com/api/v1/health/ready"
   ```

2. Confirm the login account is synthetic and unchanged:

   ```text
   admin@example.com / Admin123!
   ```

3. Confirm the frontend is using the production API base:

   ```text
   https://api.salvardata.com/api/v1
   ```

4. If production E2E fails, use the troubleshooting section in [access2-railway-custom-domain-validation.md](C:/dev/access2/docs/access2-railway-custom-domain-validation.md) before changing product code.

5. Do not enter real PHI, change Railway startup commands, or add frontend mutation controls as a demo workaround.
