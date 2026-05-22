# ACCESS2 July MVP

## Chronic-Care Workflow and Audit-Readiness Platform

App link: [https://access2.salvardata.com](https://access2.salvardata.com)

## One-Sentence Summary

ACCESS2 helps chronic-care teams show the path from patient signal to intervention, measurable outcome, review packet, and audit-ready evidence using a controlled July MVP demo with synthetic data.

## The Problem

Chronic-care organizations often do important work that is hard to prove later.

Teams may know that a patient had a signal, a care gap, an intervention, and a result. But when it is time for review, the evidence can be spread across notes, spreadsheets, systems, or manual follow-up.

That makes it harder to answer buyer-critical questions:

- Why did this patient need action?
- What did the care team do?
- What measurable result followed?
- Was the care update completed?
- What evidence supports review?
- What was approved, rejected, or corrected?
- Is the evidence organized enough for audit preparation?

## The Solution

ACCESS2 organizes the chronic-care accountability chain:

```text
signal -> escalation -> intervention -> measurable outcome -> care update -> immutable review packet -> approval/rejection -> audit-ready evidence
```

The July MVP shows how a care team can follow this chain in a controlled demo environment, preserve review evidence, and separate read-only production visibility from localhost-only correction-loop proof.

## What The July MVP Proves

- Production read-only stakeholder walkthrough at [https://access2.salvardata.com](https://access2.salvardata.com).
- Patient-level chronic-care workflow visibility.
- Outcome Evidence Readiness for reviewing whether outcome evidence is complete enough to inspect.
- Immutable review packet preservation.
- Reviewer approval/rejection workflow proof.
- Approved-only audit bundle availability.
- Local CSV dry-run/no-write validation for synthetic partner outcome data shape.
- Synthetic/demo evidence only.

## Who It Helps

ACCESS2 is designed for conversations with:

- Provider groups.
- Health systems.
- Care management organizations.
- Payer innovation teams.
- Risk-bearing provider groups.
- Chronic-care program leaders.
- Teams preparing outcome evidence for review.

## Current Validation Evidence

- July MVP walkthrough completed.
- GO decision recorded.
- 0 July must-fix items identified.
- 392 backend tests passed locally.
- Production read-only smoke passed.
- CSV dry-run/no-write safety validated.
- Snapshot immutability validated.
- Approved-only audit bundle availability validated.

## Important Boundaries

The July MVP is pilot-ready, demo-ready, and workflow-validation ready. It is not positioned as a fully production-ready SaaS product.

This MVP is not:

- A live PHI system.
- A claims submission system.
- A CMS production submission system.
- A billing system.
- An EHR or FHIR integration.
- A production mutation workflow.
- CMS-approved.
- HIPAA-certified.
- Claims-ready or billing-ready.
- Production PHI-ready.

V1 production remains read-only. V2 mutation remains localhost-only. The MVP uses synthetic/demo data only.

## Recommended Buyer Conversation

Use a 30-45 minute guided walkthrough focused on:

- The buyer's current chronic-care workflow.
- Where outcome evidence is hard to collect or prove.
- How review packets should support audit evidence preparation.
- Which chronic-care population matters most for a first pilot.
- What a small pilot should validate before broader production planning.

Good pilot questions:

- Which patient population creates the most evidence burden?
- What outcome measures matter most?
- Who reviews and approves evidence today?
- What evidence is missing most often?
- What would make audit preparation easier to trust?

## Next Step

Schedule a guided walkthrough of the ACCESS2 July MVP at:

[https://access2.salvardata.com](https://access2.salvardata.com)

The walkthrough should stay within the current MVP boundaries: production read-only demo, localhost-only correction-loop proof when needed, local CSV dry-run/no-write validation, and synthetic/demo data only.
