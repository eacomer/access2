# ACCESS2 Stakeholder Demo Package Index

## Purpose

Use this as the stakeholder-facing entry point for the current ACCESS2 demo package. It explains which docs to read, which demo path to present, and where the read-only and localhost-only boundaries sit.

This index is not a new product spec and does not authorize production mutation, staging mutation, Railway mutation, new runtime behavior, or architecture changes.

## Recommended Reading Order

1. [access2-product-release-positioning.md](C:/dev/access2/docs/access2-product-release-positioning.md) - use first for the product purpose, release posture, and stakeholder talk track.
2. [access2-v1-demo-day-script.md](C:/dev/access2/docs/access2-v1-demo-day-script.md) - use for the production read-only stakeholder walkthrough.
3. [access2-v1-demo-handoff-summary.md](C:/dev/access2/docs/access2-v1-demo-handoff-summary.md) - use for production baseline, validation evidence, and handoff map.
4. [access2-v1-demo-release-checklist.md](C:/dev/access2/docs/access2-v1-demo-release-checklist.md) - use when validating local or production demo readiness details.
5. [access2-v2-local-demo-handoff-index.md](C:/dev/access2/docs/access2-v2-local-demo-handoff-index.md) - use when introducing the localhost-only V2 correction-loop package.
6. [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md) - use only for the actual localhost V2 presenter sequence.
7. [access2-v2-checkpoint-and-roadmap.md](C:/dev/access2/docs/access2-v2-checkpoint-and-roadmap.md) - use for current proof boundaries, non-goals, staging prerequisites, and next options.

## Recommended Presenter Order

1. Open with the product positioning: ACCESS2 proves chronic-care outcome accountability by connecting signal, escalation, intervention, outcome, care update, resolution, evidence, immutable review, and audit bundle posture.
2. Run the V1 production read-only walkthrough first at `https://access2.salvardata.com`.
3. Show the four seeded production demo postures: audit-ready, missing evidence, rejected review, and override-approved review.
4. Explain the production baseline: `8 passed, 2 skipped, 0 failed`; the skips are intentional read-only mutation-path skips.
5. If the audience needs the future workflow story, switch to the V2 localhost-only correction-loop narrative.
6. Present the V2 correction loop only on verified loopback targets, or use the recorded rehearsal result if local browser tooling is unavailable.
7. Close with the current release decision: production remains read-only, V2 mutation remains localhost-only, and staging mutation waits for isolated staging approval.

## Which Demo To Use

- External stakeholder or executive overview: use the product positioning doc plus the V1 production read-only walkthrough.
- Clinical, payer, or audit reviewer conversation: use V1 production first, then explain the V2 localhost correction loop as the next controlled review lifecycle proof.
- Engineering handoff: use the V1 handoff summary, V2 local demo handoff index, and V2 checkpoint/roadmap.
- Demo-day readiness check: use the V1 demo-day script and release checklist; keep V2 local rehearsal separate unless explicitly planned.
- Future staging decision review: use the V2 checkpoint/roadmap and staging docs only after isolated staging or preview infrastructure is explicitly approved.

## V1 Production Walkthrough Summary

V1 production is the safe external demo:

- Frontend: `https://access2.salvardata.com`
- Backend API: `https://api.salvardata.com/api/v1`
- Data: synthetic demo data only.
- Posture: read-only.
- Baseline: `8 passed, 2 skipped, 0 failed`.

The V1 walkthrough shows patient/worklist views, audit-readiness posture, patient evidence panels, immutable review packet history, approved audit bundle posture, and manifest verification. It does not expose production reviewer rejection, override approval, assignment, or snapshot creation mutation controls.

## V2 Localhost Walkthrough Summary

V2 localhost is the controlled correction-loop proof:

- Frontend target: `http://localhost:3000` or verified current-workspace `http://localhost:3001`.
- API target: `http://localhost:8000/api/v1`.
- Data: disposable synthetic local demo patient only.
- Posture: localhost-only mutation.

The V2 local proof shows reviewer assignment, rejection with reason, immutable rejected snapshot history, corrected/new snapshot creation, corrected approval, `audit_bundle.available=true`, and preserved rejected snapshot backlog/history. It must not run against production, Railway, staging, `https://`, or any non-loopback target.

## Product Positioning Summary

ACCESS2 is a chronic-care outcome accountability system. The product story is:

```text
signal -> escalation -> intervention -> outcome -> care update -> resolution -> evidence -> immutable review packet -> approval/rejection -> audit bundle
```

V1 production explains and verifies the audit evidence chain safely in a read-only posture. V2 localhost proves that correction can happen without rewriting history: a rejected packet stays immutable, corrected evidence creates a new packet, and the approved latest packet becomes audit-bundle-ready.

## Proof Boundaries

- V1 production proves read-only evidence posture, audit-readiness visibility, approved audit bundle posture, and manifest verification.
- V2 localhost proves the correction-loop mutation pattern on disposable local data only.
- Production mutation is not approved.
- Staging mutation is not approved.
- Railway mutation is not approved.
- Override approval UI is not ready.
- EHR/FHIR, billing, AI, real CMS submission, and real PHI workflows are not claimed.

## Demo-Day Do Not Do

- Do not enter real PHI.
- Do not run production mutation tests.
- Do not mutate Railway, `salvardata.com`, `api.salvardata.com`, staging, `https://`, or non-loopback targets.
- Do not run V2 local mutation E2E as part of the V1 production walkthrough.
- Do not describe rejected snapshots as edited, refreshed, repaired, or overwritten.
- Do not imply EHR/FHIR, billing, AI, or real CMS submission exists.
- Do not change Railway config or the backend startup command.

## Troubleshooting Pointers

- V1 production issue: use [access2-v1-demo-day-script.md](C:/dev/access2/docs/access2-v1-demo-day-script.md) and [access2-v1-demo-handoff-summary.md](C:/dev/access2/docs/access2-v1-demo-handoff-summary.md) first.
- Production E2E or custom-domain issue: use [access2-railway-custom-domain-validation.md](C:/dev/access2/docs/access2-railway-custom-domain-validation.md).
- Production seeded data issue: use [access2-demo-data-recreation-checklist.md](C:/dev/access2/docs/access2-demo-data-recreation-checklist.md) and keep data synthetic.
- V2 local timing, stale `.next`, port, or Playwright issue: use [access2-v2-local-demo-handoff-index.md](C:/dev/access2/docs/access2-v2-local-demo-handoff-index.md) and [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md).
- Staging question: use [access2-v2-checkpoint-and-roadmap.md](C:/dev/access2/docs/access2-v2-checkpoint-and-roadmap.md); do not run staging mutation until isolated staging is explicitly approved.

## Recommended Next Decision

After stakeholder review, choose one:

- Keep V1 production as the external read-only demo and collect feedback.
- Run another V2 localhost-only presenter rehearsal if the correction-loop story needs refinement.
- Package feedback into a small docs/copy clarity slice if the proof chain is confusing.
- Begin isolated staging planning only if a separate staging or preview environment is explicitly approved.

Default recommendation: keep production read-only and use stakeholder feedback to decide whether the next slice is demo clarity or isolated staging planning. Do not expand mutation beyond localhost without explicit isolated staging approval.

Latest feedback checkpoint: [access2-stakeholder-walkthrough-feedback-and-go-no-go.md](C:/dev/access2/docs/access2-stakeholder-walkthrough-feedback-and-go-no-go.md).
