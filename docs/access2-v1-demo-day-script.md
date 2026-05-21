# ACCESS2 V1 Production Demo-Day Walkthrough

## Purpose

Use this as the external demo-day entry point for the production ACCESS2 V1 walkthrough. The goal is to show how ACCESS2 proves that a chronic-care need moved through signal, escalation, intervention, outcome, care update, evidence, immutable review, audit bundle readiness, and manifest verification.

Core evidence chain:

```text
signal -> escalation -> intervention -> outcome -> care update -> evidence -> case summary -> immutable review packet snapshot -> approval/rejection -> audit bundle -> manifest verification
```

This walkthrough is read-only. It is for a stakeholder or reviewer presentation, not for creating patients, approving packets, rejecting packets, overriding review, assigning reviewers, exporting new workflow state, or changing seeded demo data.

## Production Access

- Frontend: `https://access2.salvardata.com`
- Backend API: `https://api.salvardata.com/api/v1`
- Login: `admin@example.com` / `Admin123!`
- Data posture: synthetic/demo data only; no real PHI.
- Validation baseline: `8 passed, 2 skipped, 0 failed`

## Read-Only Guardrails

- Do not enter real PHI.
- Do not create, edit, approve, reject, override, assign, or create review-packet snapshots during the production walkthrough.
- Do not run production mutation paths or V2 localhost mutation E2E as part of this V1 production demo.
- Do not mutate Railway production data, change Railway config, or change the backend startup command.
- Treat Demo Patient 3 and Demo Patient 4 as read-only seeded postures, not live mutation targets.
- V2 correction-loop mutation remains localhost-only and separate from this V1 production walkthrough.

## Expected Seeded Demo Patients

- Demo Patient 1 - Audit Ready: `f4c31931-8fc2-41d6-9f45-9ab0bd039088`
- Demo Patient 2 - Missing Evidence: `1c5c7db8-96f8-47af-a643-741641ecdcf3`
- Demo Patient 3 - Rejected Review: `4c1ef5ef-1216-453d-b317-b965a0dd1dea`
- Demo Patient 4 - Override Approval: `2e9dc25c-2e56-4d6a-aea0-8706d33b0444`

Use these patients to show the four intended production postures: audit-ready/export-ready, missing evidence, rejected review, and override-approved review.

## Recommended Presenter Sequence

1. Open `https://access2.salvardata.com` and sign in with the synthetic demo account.
2. Open `Demo Guide` at `/demo-guide` to frame the ACCESS2 proof chain and no-PHI expectation.
3. Open `Release Summary` at `/demo/release-summary`.
4. Show the Evidence Proof Checklist across the four seeded patients.
5. Open `Reviewer Queue` at `/audit-readiness`.
6. Show lifecycle counts, latest review-packet posture, patient-detail links, next-step text, review state, and export state.
7. Open Demo Patient 1 and show the complete audit-ready path.
8. If visible, show Outcome Evidence Readiness as read-only evidence-readiness context, not CMS submission or claims submission.
9. If visible, show JSON, Markdown, and PDF audit bundle download posture for the approved/export-ready snapshot.
10. Open `/audit-bundle-verify` and explain manifest verification using a copied JSON bundle `audit_manifest`.
11. Open Demo Patient 2 to show missing evidence and readiness reasons.
12. Open Demo Patient 3 to show rejected review posture and blocked audit readiness.
13. Open Demo Patient 4 to show override-approved posture without exposing override controls.
14. Close by restating that ACCESS2 preserves immutable proof history and verifies audit bundles against persisted snapshot data.

## Page Talk Track

### Demo Guide

Say: "ACCESS2 is proving the evidence chain, not just showing a task list. This demo uses synthetic data only and keeps production read-only."

Confirm that the page explains:

- The ACCESS2 proof chain.
- Synthetic/demo-only safety expectations.
- No real PHI.
- Links or routes for the four seeded demo scenarios.

### Demo Release Summary

Say: "This is the production operator summary. It lets us verify the demo posture before opening patient-level evidence."

Show:

- Production/demo frontend posture.
- Evidence Proof Checklist.
- All four seeded patient scenarios.
- Signal, escalation, intervention, outcome, evidence, case summary, immutable review packet snapshot, review posture, audit bundle status, manifest verification, readiness reasons, and next step.
- Expected production E2E baseline: `8 passed, 2 skipped, 0 failed`.

Do not expect approve, reject, override, assign, export, or create-snapshot controls on this read-only summary.

### Reviewer Work Queue

Say: "The Reviewer Queue is a read-only posture and navigation surface in V1. It helps operators find audit-ready, blocked, rejected, override-approved, pending, and exported-bundle states without changing the audit record."

Show:

- Lifecycle counts.
- Read-only queue rows.
- Patient-detail links.
- Next-step text.
- Review and export state.

Do not look for approve, reject, override, assign, export, or create-snapshot actions here.

## Patient Walkthroughs

### Demo Patient 1 - Audit Ready

Open patient `f4c31931-8fc2-41d6-9f45-9ab0bd039088`.

Show:

- Evidence Chain panel.
- Manifest Verification panel.
- Outcome Proof Gaps panel.
- Outcome Evidence Readiness section, if present.
- Review packet backlog and approved/export-ready audit bundle posture.
- JSON, Markdown, and PDF audit bundle download availability when shown.

Say: "This patient demonstrates the complete path from signal to outcome proof, approved immutable snapshot, audit bundle availability, and manifest verification."

If Outcome Evidence Readiness is visible, say: "This is not a claim submission or CMS submission. This is the evidence-readiness layer that helps a provider prove whether the outcome story is complete enough for review. It shows the ACCESS track and condition, metric, baseline, follow-up, readiness status, completeness, and care update milestone from persisted packet evidence."

### Demo Patient 2 - Missing Evidence

Open patient `1c5c7db8-96f8-47af-a643-741641ecdcf3`.

Show:

- Outcome Proof Gaps and readiness reasons.
- Missing or incomplete outcome/evidence proof.
- Missing or incomplete Outcome Evidence Readiness, if present.
- Next-step explanation.

Say: "ACCESS2 does not treat workflow activity alone as audit-ready. The system must prove measurable outcome evidence."

### Demo Patient 3 - Rejected Review

Open patient `4c1ef5ef-1216-453d-b317-b965a0dd1dea`.

Show:

- Existing proof packet or snapshot posture.
- Rejected review state.
- Blocked export/readiness posture.

Say: "The rejected state is preserved as review history. Production V1 shows this posture without exposing a live rejection control."

### Demo Patient 4 - Override Approval

Open patient `2e9dc25c-2e56-4d6a-aea0-8706d33b0444`.

Show:

- Override-approved review posture.
- Evidence panels and manifest verification posture.
- Read-only override explanation.

Say: "ACCESS2 can surface override-approved evidence state while keeping this production frontend walkthrough read-only."

## What The Demo Proves

- A seeded operator can sign in to the production frontend.
- The Demo Guide and Release Summary explain the ACCESS2 proof chain with synthetic data.
- The Reviewer Queue shows latest review-packet posture without mutation controls.
- The four seeded patients cover audit-ready, missing-evidence, rejected-review, and override-approved postures.
- Patient detail pages show evidence, readiness reasons, immutable review-packet posture, and audit-bundle posture.
- Patient detail can show Outcome Evidence Readiness as read-only persisted packet context for ACCESS track, metric, baseline/follow-up, readiness status, completeness, and care update milestone.
- Demo Patient 1 can show approved/export-ready audit bundle posture and manifest verification.
- Audit bundle verification compares a submitted manifest against persisted snapshot data.
- Immutable review packet snapshots are presented as review history, not rebuilt live during audit reads.

## What The Demo Does Not Prove

- It does not prove production mutation workflows are enabled.
- It does not demonstrate reviewer rejection, superuser override approval, assignment, or snapshot creation through the production UI.
- It does not demonstrate V2 correction-loop mutation; V2 mutation remains localhost-only.
- It does not demonstrate claims submission, billing automation, or CMS production submission.
- It does not demonstrate EHR, FHIR, billing, payment reconciliation, AI recommendations, predictive analytics, patient portal, or real PHI workflows.

## Expected Skipped Mutation Paths

Production E2E baseline:

```text
8 passed, 2 skipped, 0 failed
```

The two skipped tests are intentional V1 read-only constraints:

- Demo Patient 3 reviewer rejection through UI.
- Demo Patient 4 superuser override approval through UI.

Reason: ACCESS2 V1 production exposes rejected and override-approved states as seeded read-only postures. It does not expose reviewer rejection or superuser override approval mutation controls in the frontend.

## Troubleshooting Pointers

- If the frontend does not load, verify `https://access2.salvardata.com`.
- If login fails, verify the synthetic demo credentials and confirm the frontend is using `https://api.salvardata.com/api/v1`.
- If pages render stale content, check the deployed custom-domain baseline in [access2-railway-custom-domain-validation.md](C:/dev/access2/docs/access2-railway-custom-domain-validation.md).
- If production E2E does not return `8 passed, 2 skipped, 0 failed`, use the troubleshooting section in [access2-railway-custom-domain-validation.md](C:/dev/access2/docs/access2-railway-custom-domain-validation.md) before changing product code.
- If seeded patient pages are missing, use [access2-demo-data-recreation-checklist.md](C:/dev/access2/docs/access2-demo-data-recreation-checklist.md) and keep production demo data synthetic.
- If JSON, Markdown, or PDF bundle links are unavailable, confirm the selected snapshot is approved/export-ready; do not force a live production mutation.

Production health checks, if needed:

```powershell
Invoke-RestMethod "https://api.salvardata.com/api/v1/health/live"
Invoke-RestMethod "https://api.salvardata.com/api/v1/health/ready"
```

Do not use troubleshooting as a reason to enter PHI, run production mutation tests, change Railway startup commands, or add mutation controls.

## Close

Say: "ACCESS2 V1 demonstrates a read-only production evidence path: synthetic patients, visible proof gaps, immutable review-packet history, approved audit bundle posture, and manifest verification against persisted data. The skipped mutation paths are intentional because production V1 remains read-only."
