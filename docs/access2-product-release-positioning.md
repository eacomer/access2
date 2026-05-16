# ACCESS2 Product Release Positioning

## Purpose

Use this as the compact product and release explanation for ACCESS2 V1 production and the V2 localhost-only correction-loop proof.

ACCESS2 is a chronic-care outcome accountability system. Its purpose is to prove that a patient need moved through action, measurable outcome, review, and audit-ready evidence without losing the history of what was reviewed.

Core proof chain:

```text
signal -> escalation -> intervention -> outcome -> care update -> resolution -> evidence -> immutable review packet -> approval/rejection -> audit bundle
```

## Product Frame

ACCESS2 is not just a task list. It is built around the question an operator, reviewer, or payer will eventually ask:

```text
What happened, what changed for the patient, what evidence supports that change, who reviewed it, and can the audit artifact be verified?
```

That means the product value is in the defensible chain between workflow activity and outcome proof:

- A signal or care gap identifies why action was needed.
- An escalation and intervention record what action was taken.
- Outcome, care update, and resolution evidence show whether the intervention worked.
- A review packet freezes the evidence posture for review.
- Approval or rejection records the review decision.
- An audit bundle packages the persisted evidence for export and verification.

## What V1 Production Proves

ACCESS2 V1 production proves the read-only audit evidence story using synthetic demo data:

- A seeded operator can sign in at `https://access2.salvardata.com`.
- Production API posture is available at `https://api.salvardata.com/api/v1`.
- The demo can show patient/worklist views, audit-readiness posture, patient evidence panels, immutable review packet history, approved audit bundle posture, and manifest verification.
- The four seeded demo patients cover audit-ready, missing-evidence, rejected-review, and override-approved postures.
- Production E2E is documented at `8 passed, 2 skipped, 0 failed`.
- The skipped tests are intentional because reviewer rejection through UI and superuser override approval through UI are not enabled as production mutation workflows.

V1 production remains read-only because the shared production demo tenant must stay stable for external walkthroughs. It is a proof and explanation surface, not a mutable workflow environment.

## What V2 Localhost Proves

ACCESS2 V2 localhost-only proof shows the controlled correction loop after a reviewer decision:

- Assign the latest `pending_review` packet.
- Reject that packet with a reason.
- Preserve the rejected packet as immutable, terminal history.
- Correct the current synthetic evidence posture.
- Create a new immutable review packet snapshot.
- Approve the corrected latest packet when persisted evidence is complete.
- Show `audit_bundle.available=true` after approval.
- Keep prior rejected snapshots visible in backlog/history without editing or overwriting them.

V2 mutation remains localhost-only because mutation testing needs disposable data, explicit loopback targets, repeatable reset/seed behavior, and fail-closed host guards. Production and Railway targets are not acceptable mutation targets.

## What Staging Would Need Next

Any next mutation expansion should wait for an explicitly approved isolated staging or preview environment with:

- Separate frontend, API, database, tenant, and seed data from production.
- Synthetic-only data.
- Deterministic seed/reset ownership.
- Host guards that refuse production, Railway production, custom-domain, `https://`, and non-approved targets for mutation E2E.
- Clear teardown and recovery steps.
- Separate mutation E2E from the production read-only E2E suite.
- Explicit approval before any staging mutation run.

Without those conditions, V2 mutation should stay localhost-only.

## What ACCESS2 Does Not Yet Claim

ACCESS2 does not yet claim:

- Production mutation workflows are enabled.
- Staging mutation is approved.
- Real CMS submission is implemented.
- EHR or FHIR integration exists.
- Billing or payment reconciliation exists.
- AI recommendations, predictive analytics, patient portal, mobile app, or broad admin workflows exist.
- Real PHI is supported for these demos.
- Superuser override approval UI is ready for production.

## Stakeholder Talk Track

Use this concise framing:

```text
ACCESS2 proves chronic-care accountability. It starts with a patient signal, follows the escalation and intervention, checks whether a measurable outcome occurred, captures the care update and resolution evidence, freezes that evidence into an immutable review packet, records approval or rejection, and packages the approved proof into an audit bundle.
```

For V1 production:

```text
Today production is read-only. It demonstrates the evidence posture safely with synthetic data, including audit-ready, missing-evidence, rejected, and override-approved scenarios. The expected production E2E baseline is 8 passed, 2 skipped, and 0 failed; the skips are intentional because production mutation controls remain disabled.
```

For V2 localhost:

```text
The localhost V2 proof shows how ACCESS2 handles correction without rewriting history. A rejected packet stays immutable. Corrected evidence creates a new packet. The corrected packet can be approved locally, and the prior rejected packet remains part of the audit trail.
```

Close with:

```text
The current release posture is deliberate: V1 production explains and verifies the audit evidence chain read-only; V2 localhost proves the next mutation pattern on disposable local data; staging comes only after isolated infrastructure and reset controls are approved.
```
