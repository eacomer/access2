# ACCESS2 Stakeholder Demo Package Index

## Purpose

Use this as the stakeholder-facing entry point for the current ACCESS2 demo package. It explains which docs to read, which demo path to present, and where the read-only and localhost-only boundaries sit.

This index is not a new product spec and does not authorize production mutation, staging mutation, Railway mutation, new runtime behavior, or architecture changes.

## Recommended Reading Order

1. [access2-product-release-positioning.md](C:/dev/access2/docs/access2-product-release-positioning.md) - use first for the product purpose, release posture, and stakeholder talk track.
2. [access2-july-mvp-buyer-one-pager.md](C:/dev/access2/docs/access2-july-mvp-buyer-one-pager.md) - use as the buyer-facing one-page summary for prospective purchaser conversations, pilot positioning, validation evidence, and boundaries.
3. [access2-july-mvp-user-guide.md](C:/dev/access2/docs/access2-july-mvp-user-guide.md) - use as the plain-language July MVP guide for non-technical and mixed stakeholders, including screenshot captions and placeholders.
4. [access2-july-mvp-non-clinical-tester-guide.md](C:/dev/access2/docs/access2-july-mvp-non-clinical-tester-guide.md) - use when a browser-capable tester needs plain-language background, checklists, defect examples, and environment safety boundaries without clinical context.
5. [access2-july-mvp-readiness-plan.md](C:/dev/access2/docs/access2-july-mvp-readiness-plan.md) - use to separate what can be shown now, what can be pilot-positioned by July, and what remains future production hardening.
6. [access2-july-mvp-final-rehearsal-and-go-no-go.md](C:/dev/access2/docs/access2-july-mvp-final-rehearsal-and-go-no-go.md) - use for the final operator rehearsal, validation evidence summary, stakeholder questions, July must-fix template, decision criteria, and go/no-go capture path.
7. [access2-external-csv-intake-spec.md](C:/dev/access2/docs/access2-external-csv-intake-spec.md) - use when stakeholders ask how approved pilot or partner outcome records could enter the ACCESS2 proof chain without FHIR/EHR integration yet.
8. [access2-v1-demo-day-script.md](C:/dev/access2/docs/access2-v1-demo-day-script.md) - use for the production read-only stakeholder walkthrough.
9. [access2-v1-demo-handoff-summary.md](C:/dev/access2/docs/access2-v1-demo-handoff-summary.md) - use for production baseline, validation evidence, and handoff map.
10. [access2-v1-demo-release-checklist.md](C:/dev/access2/docs/access2-v1-demo-release-checklist.md) - use when validating local or production demo readiness details.
11. [access2-v2-local-demo-handoff-index.md](C:/dev/access2/docs/access2-v2-local-demo-handoff-index.md) - use when introducing the localhost-only V2 correction-loop package.
12. [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md) - use only for the actual localhost V2 presenter sequence.
13. [access2-v2-checkpoint-and-roadmap.md](C:/dev/access2/docs/access2-v2-checkpoint-and-roadmap.md) - use for current proof boundaries, non-goals, staging prerequisites, and next options.

## Recommended Presenter Order

1. Open with the product positioning: ACCESS2 proves chronic-care outcome accountability by connecting signal, escalation, intervention, outcome, care update, resolution, evidence, immutable review, and audit bundle posture.
2. Use the July MVP readiness plan to frame the distinction between what can be shown now, what can be pilot-positioned by July, and what remains future production hardening.
3. Run the V1 production read-only walkthrough first at `https://access2.salvardata.com`.
4. Show the four seeded production demo postures: audit-ready, missing evidence, rejected review, and override-approved review.
5. On patient detail, call out Outcome Evidence Readiness when visible: ACCESS track, qualifying condition, metric, baseline, follow-up, readiness status, evidence completeness, and care update milestone.
6. Explain the production baseline: `8 passed, 2 skipped, 0 failed`; the skips are intentional read-only mutation-path skips.
7. If the audience needs the future workflow story, switch to the V2 localhost-only correction-loop narrative.
8. Present the V2 correction loop only on verified loopback targets, or use the recorded rehearsal result if local browser tooling is unavailable.
9. Use the local CSV dry-run result to explain how a synthetic partner outcome file can be validated before any import or persistence exists.
10. Close with the current release decision: production remains read-only, V2 mutation remains localhost-only, July MVP/pilot readiness includes a bounded external CSV intake requirement/spec candidate, and staging mutation waits for isolated staging approval.

## Which Demo To Use

- External stakeholder or executive overview: use the product positioning doc plus the V1 production read-only walkthrough.
- Clinical, payer, or audit reviewer conversation: use V1 production first, then explain the V2 localhost correction loop as the next controlled review lifecycle proof.
- Engineering handoff: use the V1 handoff summary, V2 local demo handoff index, and V2 checkpoint/roadmap.
- Demo-day readiness check: use the V1 demo-day script and release checklist; keep V2 local rehearsal separate unless explicitly planned.
- Future staging decision review: use the V2 checkpoint/roadmap and staging docs only after isolated staging or preview infrastructure is explicitly approved.
- Buyer conversation: use [access2-july-mvp-buyer-one-pager.md](C:/dev/access2/docs/access2-july-mvp-buyer-one-pager.md) for a scannable July MVP summary that explains the problem, solution, validation evidence, buyer fit, and current MVP boundaries.
- July MVP/pilot-readiness conversation: use [access2-july-mvp-readiness-plan.md](C:/dev/access2/docs/access2-july-mvp-readiness-plan.md) to explain the May 21, 2026 checkpoint, what can be shown now, what can be pilot-positioned by July, and what remains future production hardening.
- Final July rehearsal or go/no-go decision: use [access2-july-mvp-final-rehearsal-and-go-no-go.md](C:/dev/access2/docs/access2-july-mvp-final-rehearsal-and-go-no-go.md) for the practical presenter sequence, validation evidence summary, stakeholder questions, decision criteria, July must-fix template, and capture path.
- Plain-language July MVP guide: use [access2-july-mvp-user-guide.md](C:/dev/access2/docs/access2-july-mvp-user-guide.md) for non-technical and mixed stakeholders who need a short explanation of V1 production read-only usage, V2 localhost-only correction-loop proof, local CSV dry-run validation, screenshots, and guardrails.
- Non-clinical MVP tester: use [access2-july-mvp-non-clinical-tester-guide.md](C:/dev/access2/docs/access2-july-mvp-non-clinical-tester-guide.md) when a tester can use a browser and follow steps but needs plain-language background, glossary terms, defect examples, and environment safety boundaries before testing.
- External intake conversation: use [access2-external-csv-intake-spec.md](C:/dev/access2/docs/access2-external-csv-intake-spec.md) to explain the controlled CSV template, validation/rejection posture, source/batch metadata, and why this is not FHIR/EHR integration, CMS production submission, claims ingestion, or billing automation.

## V1 Production Walkthrough Summary

V1 production is the safe external demo:

- Frontend: `https://access2.salvardata.com`
- Backend API: `https://api.salvardata.com/api/v1`
- Data: synthetic demo data only.
- Posture: read-only.
- Baseline: `8 passed, 2 skipped, 0 failed`.
- Strict no-data-change post-deploy copy check: use `npm run test:e2e:production-readonly-smoke`; use the full production E2E suite only when recording audit export events is acceptable.

The V1 walkthrough shows patient/worklist views, audit-readiness posture, patient evidence panels, Outcome Evidence Readiness when persisted packet data is available, immutable review packet history, approved audit bundle posture, and manifest verification. It does not expose production reviewer rejection, override approval, assignment, or snapshot creation mutation controls.

## V2 Localhost Walkthrough Summary

V2 localhost is the controlled correction-loop proof:

- Frontend target: `http://localhost:3000` or verified current-workspace `http://localhost:3001`.
- API target: `http://localhost:8000/api/v1`.
- Data: disposable synthetic local demo patient only.
- Posture: localhost-only mutation.

The V2 local proof shows reviewer assignment, rejection with reason, immutable rejected snapshot history, corrected/new snapshot creation, corrected approval, `audit_bundle.available=true`, Outcome Evidence Readiness for synthetic ACCESS track evidence, and preserved rejected snapshot backlog/history. It must not run against production, Railway, staging, `https://`, or any non-loopback target.

## Outcome Evidence Readiness Talk Track

Use this short explanation when the patient detail page shows the Outcome Evidence Readiness section:

```text
This is not a claim submission or CMS submission. This is the evidence-readiness layer that helps a provider prove whether the outcome story is complete enough for review.
```

The section is read-only. It uses persisted review packet data and shows the ACCESS clinical track and qualifying condition, the metric being reviewed, baseline and follow-up evidence, outcome readiness status, evidence completeness, and the care update milestone. In the current demo, this uses synthetic local/demo data only.

Plain-English value proposition: ACCESS2 is connecting the chain from signal to intervention to measurable outcome to care update to immutable review packet to audit-ready evidence. The readiness section helps stakeholders see whether the clinical outcome story is complete enough to review; it is not CMS production submission, claims submission, billing automation, or proof that production mutation is enabled.

## July MVP Operator Rehearsal Package

Use this package when the stakeholder conversation needs the full July MVP and pilot-readiness story:

- V1 production read-only demo: current production walkthrough with synthetic data, read-only evidence posture, approved audit bundle posture, and manifest verification.
- V2 localhost-only correction loop: disposable local data proof that rejection preserves immutable history and a corrected latest packet can become audit-bundle-ready.
- Outcome Evidence Readiness: read-only patient-detail proof that ACCESS track outcome evidence, baseline/follow-up, readiness status, completeness, and care update milestone help reviewers see whether the outcome story is complete enough for review.
- Local external CSV dry-run validation: synthetic fixture validated by `backend/scripts/validate_external_csv_intake.py` with `row count: 2`, `accepted row count: 2`, and `rejected row count: 0`; the recorded operator checkpoint is in [access2-external-csv-intake-spec.md](C:/dev/access2/docs/access2-external-csv-intake-spec.md).

This is pilot-positioned evidence, not full production-user readiness. The CSV validator is dry-run/no-write; V1 production remains read-only; V2 mutation remains localhost-only; and the package does not claim real PHI intake, CMS production submission, FHIR/EHR integration, billing/claims ingestion, staging mutation, or production mutation.

The final rehearsal evidence summary lives in [access2-july-mvp-final-rehearsal-and-go-no-go.md](C:/dev/access2/docs/access2-july-mvp-final-rehearsal-and-go-no-go.md). It should be treated as recorded evidence only, not as authorization to rerun production mutation, staging, or V2 mutation suites during the stakeholder walkthrough.

## Product Positioning Summary

ACCESS2 is a chronic-care outcome accountability system. The product story is:

```text
signal -> escalation -> intervention -> outcome -> care update -> resolution -> evidence -> immutable review packet -> approval/rejection -> audit bundle
```

V1 production explains and verifies the audit evidence chain safely in a read-only posture. V2 localhost proves that correction can happen without rewriting history: a rejected packet stays immutable, corrected evidence creates a new packet, and the approved latest packet becomes audit-bundle-ready.

## Proof Boundaries

- V1 production proves read-only evidence posture, audit-readiness visibility, approved audit bundle posture, and manifest verification.
- V1 and V2 walkthroughs can show Outcome Evidence Readiness as a read-only explanation of clinical track, metric, baseline/follow-up, readiness status, completeness, and care update milestone when persisted packet evidence is available.
- V2 localhost proves the correction-loop mutation pattern on disposable local data only.
- Production mutation is not approved.
- Staging mutation is not approved.
- Railway mutation is not approved.
- Override approval UI is not ready.
- EHR/FHIR, billing, claims submission, AI, real CMS submission, and real PHI workflows are not claimed.

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
- Strict post-deploy Demo Guide/copy check: use [access2-v1-demo-guide-clarity-validation.md](C:/dev/access2/docs/access2-v1-demo-guide-clarity-validation.md) and run `npm run test:e2e:production-readonly-smoke`.
- Full production E2E or custom-domain issue: use [access2-railway-custom-domain-validation.md](C:/dev/access2/docs/access2-railway-custom-domain-validation.md). Do not use the full suite for strict no-data-change validation because audit bundle export/download paths can record `audit_bundle_exported` events.
- Production seeded data issue: use [access2-demo-data-recreation-checklist.md](C:/dev/access2/docs/access2-demo-data-recreation-checklist.md) and keep data synthetic.
- V2 local timing, stale `.next`, port, or Playwright issue: use [access2-v2-local-demo-handoff-index.md](C:/dev/access2/docs/access2-v2-local-demo-handoff-index.md) and [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md).
- Staging question: use [access2-v2-checkpoint-and-roadmap.md](C:/dev/access2/docs/access2-v2-checkpoint-and-roadmap.md); do not run staging mutation until isolated staging is explicitly approved.

## Recommended Next Decision

Before stakeholder review, run the final rehearsal in [access2-july-mvp-final-rehearsal-and-go-no-go.md](C:/dev/access2/docs/access2-july-mvp-final-rehearsal-and-go-no-go.md). After stakeholder review, choose one:

- Keep V1 production as the external read-only demo and collect feedback.
- Run another V2 localhost-only presenter rehearsal if the correction-loop story needs refinement.
- Package feedback into a small docs/copy clarity slice if the proof chain is confusing.
- Begin isolated staging planning only if a separate staging or preview environment is explicitly approved.

Default recommendation: keep production read-only and use stakeholder feedback to decide whether the next slice is demo clarity or isolated staging planning. Do not expand mutation beyond localhost without explicit isolated staging approval.

Latest feedback checkpoint: [access2-stakeholder-walkthrough-feedback-and-go-no-go.md](C:/dev/access2/docs/access2-stakeholder-walkthrough-feedback-and-go-no-go.md).

## Second Walkthrough Capture Checklist

For the next stakeholder walkthrough, reuse the same package and capture only decision-useful feedback:

- Confirm whether the chronic-care outcome accountability story is clear.
- Confirm whether the Outcome Evidence Readiness section is understandable as readiness evidence, not CMS/claims/billing submission.
- Confirm whether immutable review packets and preserved rejected history are clear.
- Confirm whether audit bundle posture and manifest verification are clear.
- Confirm whether the V1 production read-only boundary and V2 localhost-only mutation boundary are clear.
- Record concrete confusion, objections, or follow-up questions.
- Record any request for staging, production mutation, EHR/FHIR, billing, AI, admin features, or override approval as follow-up only.
- Use the reusable capture block in [access2-stakeholder-walkthrough-feedback-and-go-no-go.md](C:/dev/access2/docs/access2-stakeholder-walkthrough-feedback-and-go-no-go.md) after the walkthrough.
