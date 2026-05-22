# ACCESS2 July MVP Final Rehearsal And Go/No-Go Package

Date/checkpoint: May 21, 2026

## Purpose

Use this document for the final ACCESS2 July MVP walkthrough rehearsal before stakeholder review. The goal is to confirm that the presenter can explain the complete July MVP story in a practical sequence:

```text
signal -> escalation -> intervention -> measurable outcome -> care update -> immutable review packet -> approval/rejection -> audit-ready evidence
```

This is a rehearsal and feedback-capture package. It is not a new product spec, does not approve new runtime behavior, and does not authorize staging or production mutation.

## Current Scope And Guardrails

- V1 production remains read-only.
- V2 mutation remains localhost-only.
- CSV validation remains local dry-run/no-write.
- Use synthetic/demo data only.
- Do not enter, paste, import, or discuss real PHI as live patient data.
- Do not run staging or production mutation tests.
- Do not run local mutation E2E as part of the production V1 walkthrough.
- Do not add claims submission, CMS production submission, billing automation, EHR/FHIR integration, AI features, override approval, or broad admin workflows.
- Persisted immutable snapshot and audit bundle content must be read from stored `packet_json` and `packet_markdown`; do not rebuild immutable packet or audit bundle content on read.

## What The Demo Proves Today

- V1 production can show a safe read-only evidence and audit-readiness walkthrough using synthetic data.
- Patient detail can explain Outcome Evidence Readiness from persisted packet evidence: ACCESS track, metric, baseline/follow-up, readiness status, evidence completeness, and care update milestone.
- V2 localhost can show the correction-loop proof on disposable synthetic local data: assignment, rejection, preserved rejected history, corrected/new immutable snapshot creation, corrected approval, and `audit_bundle.available=true`.
- Local CSV dry-run validation can show how a synthetic partner outcome record could be checked before import or persistence exists.
- ACCESS2 can connect signal, intervention, measurable outcome, care update, immutable review, and audit-ready evidence in a stakeholder-readable chain.

## Validation Evidence Summary

Use this as the single rehearsal evidence summary. It records already captured validation evidence; it is not approval to rerun production mutation, staging, or local mutation E2E during the walkthrough.

- V1 production read-only smoke: `npm run test:e2e:production-readonly-smoke` passed with `1 passed`. This was a strict no-data-change smoke check only; it did not run production mutation, staging mutation, or audit bundle export validation.
- V2 localhost-only correction-loop proof: the local disposable synthetic flow previously proved assignment, rejection, preserved rejected packet history, corrected/new immutable snapshot creation, corrected approval, and `audit_bundle.available=true` on loopback targets only.
- Local CSV dry-run/no-write validation: `backend/scripts/validate_external_csv_intake.py` validated `docs/examples/access2_external_csv_intake_valid_sample.csv` with `row count: 2`, `accepted row count: 2`, and `rejected row count: 0`, with no database, network, or file-write operations.
- Outcome Evidence Readiness display: patient detail can show ACCESS track, qualifying condition, metric, baseline/follow-up, readiness status, evidence completeness, and care update milestone from persisted packet evidence as read-only review readiness.

Evidence boundaries:

- Production validation remains read-only.
- V2 mutation evidence remains localhost-only.
- CSV validation remains local dry-run/no-write.
- None of this is CMS production submission, claims submission, billing automation, real PHI intake, staging mutation, production mutation, EHR/FHIR integration, AI, or broad admin scope.

## July MVP Readiness Package Completion - May 22, 2026

The July MVP readiness package is complete for a live final walkthrough rehearsal when the presenter can use this document from start to finish without tribal knowledge.

Completion status:

- Final walkthrough rehearsal path: complete in this document.
- Validation evidence summary: complete in this document and bounded to recorded safe evidence.
- Stakeholder feedback capture path: complete through [access2-stakeholder-walkthrough-feedback-and-go-no-go.md](C:/dev/access2/docs/access2-stakeholder-walkthrough-feedback-and-go-no-go.md).
- Go / conditional go / no-go criteria: complete in this document.
- July must-fix template: complete in this document.
- Main project doc routing: complete through the July readiness plan, stakeholder package index, V2 checkpoint/roadmap, V2 planning outline, and stakeholder feedback/go-no-go note.

Current recommendation before live July feedback:

- Recommendation: `conditional go` for conducting the live July MVP stakeholder walkthrough using the current package.
- Reason: the rehearsal package, recorded validation evidence, stakeholder capture prompts, must-fix template, and decision criteria are ready, but actual July package feedback is not yet recorded.
- Required next evidence: live stakeholder feedback covering V1 production read-only, Outcome Evidence Readiness, V2 localhost-only correction loop, local CSV dry-run/no-write validation, questions/objections, July must-fix items, and final go / conditional go / no-go recommendation.
- Explicit non-authorization: this checkpoint does not approve production mutation, staging mutation, real PHI, CMS production submission, claims ingestion, billing automation, EHR/FHIR integration, AI features, broad admin scope, or rebuilding persisted immutable packet/audit-bundle content on read.

## What The Demo Does Not Prove

- It does not prove production mutation is enabled.
- It does not prove staging mutation is approved or available.
- It does not prove real PHI readiness.
- It does not submit claims, submit to CMS, perform billing, or automate payment reconciliation.
- It does not provide EHR/FHIR integration.
- It does not create patient, evidence, review packet, audit bundle, database, API, or frontend state from the CSV dry-run.
- It does not rebuild immutable packet or audit bundle content during read paths.

## Required Pre-Demo Checks

- Confirm `git status -sb` is clean or that any pending changes are known and docs-only.
- Confirm recent commits include:
  - `Add local ACCESS track outcome evidence readiness`
  - `Display ACCESS track outcome evidence read-only`
  - `Document outcome evidence readiness walkthrough`
  - `Checkpoint July MVP readiness after outcome evidence`
- Confirm the presenter has [access2-stakeholder-demo-package-index.md](C:/dev/access2/docs/access2-stakeholder-demo-package-index.md) open as the package entry point.
- Confirm the presenter has [access2-v1-demo-day-script.md](C:/dev/access2/docs/access2-v1-demo-day-script.md) ready for the production read-only walkthrough.
- Confirm the presenter has [access2-v2-local-demo-handoff-index.md](C:/dev/access2/docs/access2-v2-local-demo-handoff-index.md) and [access2-v2-local-demo-operator-script.md](C:/dev/access2/docs/access2-v2-local-demo-operator-script.md) ready if showing the localhost-only correction loop.
- Confirm the presenter has [access2-external-csv-intake-spec.md](C:/dev/access2/docs/access2-external-csv-intake-spec.md) ready for the CSV dry-run/no-write validation narrative.
- Confirm the feedback recorder has [access2-stakeholder-walkthrough-feedback-and-go-no-go.md](C:/dev/access2/docs/access2-stakeholder-walkthrough-feedback-and-go-no-go.md) open before the walkthrough begins.
- Confirm no production, Railway, staging, `https://`, or non-loopback mutation target will be used.
- Confirm no secrets or real credentials are pasted into screenshots, docs, logs, chats, or tickets.
- Confirm the presenter treats this document's Validation Evidence Summary as recorded evidence, not as authorization to rerun broad tests or mutation suites.

## Step-By-Step Walkthrough Order

### 1. V1 Production Read-Only Demo

Open the production read-only demo at:

```text
https://access2.salvardata.com
```

Show:

- Demo Guide and Release Summary.
- Reviewer Queue as read-only posture and navigation.
- Seeded synthetic patient detail pages.
- Evidence Chain, Outcome Proof Gaps, review packet history, approved audit bundle posture, and manifest verification.

Say:

```text
This is the safe external demo. It uses synthetic data and shows audit-readiness evidence without exposing production mutation controls.
```

### 2. Outcome Evidence Readiness Read-Only Display

On patient detail, point to the Outcome Evidence Readiness section when persisted packet evidence is available.

Show:

- ACCESS track and qualifying condition.
- Metric.
- Baseline and follow-up evidence.
- Outcome readiness status.
- Evidence completeness.
- Care update milestone.

Say:

```text
This is not a claim submission or CMS submission. This is the evidence-readiness layer that helps a provider prove whether the outcome story is complete enough for review.
```

### 3. V2 Localhost-Only Correction-Loop Proof

Use a verified loopback frontend and API target only:

```text
http://localhost:3000
http://localhost:3001
http://localhost:8000/api/v1
```

Show or narrate:

- Disposable synthetic local patient.
- Latest pending packet assignment.
- Rejection with reason.
- Preserved rejected packet history.
- Corrected/new immutable snapshot.
- Corrected approval.
- `audit_bundle.available=true`.

Say:

```text
The old rejected packet is not repaired or overwritten. The corrected current evidence creates a new immutable packet, and only the corrected latest packet proceeds to approval.
```

Stop if any target is production-like, Railway-like, staging, `https://`, or non-loopback.

### 4. Local CSV Dry-Run/No-Write Validation

Use [access2-external-csv-intake-spec.md](C:/dev/access2/docs/access2-external-csv-intake-spec.md) and the synthetic fixture:

```text
docs/examples/access2_external_csv_intake_valid_sample.csv
```

Show or narrate the recorded dry-run result:

```text
row count: 2
accepted row count: 2
rejected row count: 0
```

Say:

```text
This is dry-run validation only. It does not create patients, evidence, review packets, audit bundles, database rows, API state, or frontend state.
```

### 5. Stakeholder Feedback Capture

Open [access2-stakeholder-walkthrough-feedback-and-go-no-go.md](C:/dev/access2/docs/access2-stakeholder-walkthrough-feedback-and-go-no-go.md) and capture feedback during the walkthrough.

Capture:

- What landed well.
- What caused confusion.
- Questions or objections.
- Whether V1 read-only, V2 localhost-only, Outcome Evidence Readiness, and CSV dry-run/no-write boundaries were clear.
- Any July must-fix items.
- Any future hardening requests.
- Final go / conditional go / no-go recommendation.

Keep the recommendation at `conditional go` until actual July package feedback is captured. Move to `go` only when the criteria below are satisfied from live stakeholder feedback, not from earlier package preparation.

## Presenter Talk Track

Use this concise talk track:

```text
ACCESS2 is an evidence and audit-readiness system for chronic-care accountability. The July MVP package shows how a signal becomes an intervention, how the intervention is tied to measurable outcome evidence, how a care update supports review, and how that evidence is captured in an immutable review packet and audit-ready posture.

The production V1 demo is read-only and synthetic. The V2 correction loop is localhost-only and synthetic. Outcome Evidence Readiness helps the reviewer see whether the outcome story is complete enough for review. CSV validation is local dry-run only. None of this is claims submission, CMS production submission, billing, real PHI intake, or production mutation.
```

## Stakeholder Questions To Ask

- Is the chronic-care outcome accountability story clear?
- Is it clear what ACCESS2 can show today in production?
- Is it clear that V1 production remains read-only?
- Is it clear that V2 mutation remains localhost-only?
- Is Outcome Evidence Readiness understandable as review readiness, not submission or billing?
- Is the path from measurable outcome to care update to immutable review packet clear?
- Is the audit bundle handoff point clear?
- Is the CSV dry-run/no-write boundary clear?
- What would a provider, payor, CMS-oriented reviewer, or patient-facing audience need clarified before July?
- What is a true July must-fix versus future production hardening?

## Go / Conditional Go / No-Go Criteria

Use `go` only if:

- Stakeholders understand the ACCESS2 proof chain.
- V1 production read-only posture is clear.
- V2 localhost-only mutation posture is clear.
- Outcome Evidence Readiness is clear as review readiness.
- CSV dry-run/no-write posture is clear.
- No July-blocking confusion or evidence gap is identified.

Use `conditional go` if:

- The core story is credible, but one or more docs/copy/demo-flow clarifications are needed before broader stakeholder reuse.
- The needed fixes are bounded to docs, copy, presenter notes, or rehearsal polish.
- No one is asking to treat staging, production mutation, CMS submission, claims, billing, or real PHI as July-ready.
- Actual July package feedback is not yet captured, but the package is ready for a live walkthrough.

Use `no-go` if:

- Stakeholders cannot understand the evidence-to-audit-bundle story.
- The V1 production read-only or V2 localhost-only boundary is materially unclear.
- Outcome Evidence Readiness is mistaken for CMS submission, claims submission, or billing.
- CSV dry-run validation is mistaken for import/persistence.
- A concrete July blocker requires product, compliance, staging, or mutation work that has not been approved.

## July Must-Fix List Template

Use this only for items that block a credible July MVP or pilot-positioned walkthrough.

```text
Must-fix item:
Why it blocks July MVP readiness:
Evidence source or stakeholder quote:
Owner:
Required by:
Fix type: docs / copy / demo rehearsal / product implementation requiring separate approval
Guardrails affected:
Evidence needed for closure:
Status:
```

## Automated Testing Validation Results - May 22, 2026

The automated testing validation script has been executed against the active local build in the localhost environment (Docker Compose containers: `access2-backend`, `access2-frontend`, `access2-postgres`, `access2-redis`). 

All **392 tests passed successfully** in `854.14 seconds`. The details of the validated test cases are summarized below:

### 1. CSV Validator Intake Pipeline (TC-006 / TC-007)
* **Test File:** `backend/tests/test_validate_external_csv_intake.py`
* **Proof & Constraints Asserted:**
  - Mocked the CSV validator intake pipeline and ran synthetic fixture files through `validate_external_csv_intake`.
  - Asserted zero database writes, API mutations, or state modifications are executed.
  - Test `test_validator_script_imports_no_app_db_or_network_modules` uses Abstract Syntax Trees (AST) to verify that `scripts/validate_external_csv_intake.py` imports no application, database (`app`, `sqlalchemy`), or network (`requests`, `httpx`, `socket`) modules, guaranteeing strict read-only dry-run isolation.
* **Status:** **PASSED**

### 2. Snapshot Rejection & Correction-Loop (TC-003 / TC-004)
* **Test File:** `backend/tests/test_access_review_packet.py` (specifically `test_access_review_packet_snapshot_review_can_be_approved_and_rejected_without_mutating_packet`)
* **Proof & Constraints Asserted:**
  - Triggered simulated snapshot rejection (status updated to `"rejected"` with a reason).
  - Asserted that the rejected snapshot becomes an immutable, read-only historic log where `packet_json` and `packet_markdown` do NOT mutate (asserted to remain strictly equal to their original state at creation).
  - Validated that correcting the underlying evidence allows the creation of a distinct, new corrected snapshot, leaving the rejected history intact.
* **Status:** **PASSED**

### 3. Audit Bundle Availability Flag (`audit_bundle.available`)
* **Test File:** `backend/tests/test_access_review_packet.py` (specifically `test_access_review_packet_snapshot_audit_bundle_returns_approved_snapshot` and `test_access_review_packet_snapshot_audit_manifest_rejected_snapshot_conflicts`)
* **Proof & Constraints Asserted:**
  - Verified that the flag `audit_bundle.available` (or `audit_bundle_available` in database/API events) is only evaluated as `true` on the approved local snapshot version.
  - Verified that a rejected snapshot blocks any audit bundle retrieval or verification, raising an `AccessReviewPacketAuditBundleConflictError` and returning an HTTP 409 Conflict.
* **Status:** **PASSED**

### Test Pass/Fail Logs
```text
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
cachedir: .tmp/pytest_cache
rootdir: /app
configfile: pyproject.toml
plugins: anyio-4.13.0
collected 392 items

tests/test_access_case_summary.py .......                                [  1%]
tests/test_access_review_packet.py ..................................... [ 11%]
...............................................................          [ 27%]
tests/test_admin_workflow_bootstrap.py ...                               [ 28%]
tests/test_auth.py .....                                                 [ 29%]
tests/test_authorization.py ........                                     [ 31%]
tests/test_care_updates.py ...........                                   [ 34%]
tests/test_check_staging_v2_seed_reset_contract.py ................      [ 38%]
tests/test_escalation_resolution.py ......                               [ 39%]
tests/test_intervention_tasks.py ...............                         [ 43%]
tests/test_organizations.py .....                                        [ 44%]
tests/test_outcomes.py ......                                            [ 46%]
tests/test_patient_timeline.py ......................................... [ 56%]
........................................................................ [ 75%]
........................................................                 [ 89%]
tests/test_patients.py .......                                           [ 91%]
tests/test_seed_railway_demo_cases.py .......                            [ 93%]
tests/test_signals.py ..........                                         [ 95%]
tests/test_users.py ......                                               [ 97%]
tests/test_validate_external_csv_intake.py ...........                   [100%]

================== 392 passed, 1 warning in 854.14s (0:14:14) ==================
```


## Post-Walkthrough Documentation Update Instructions

After the walkthrough:

1. Update [access2-stakeholder-walkthrough-feedback-and-go-no-go.md](C:/dev/access2/docs/access2-stakeholder-walkthrough-feedback-and-go-no-go.md) with the actual audience, questions, objections, must-fix items, and go / conditional go / no-go recommendation.
2. If the feedback changes July readiness, add a dated note to [access2-july-mvp-readiness-plan.md](C:/dev/access2/docs/access2-july-mvp-readiness-plan.md).
3. If the feedback changes package routing, update [access2-stakeholder-demo-package-index.md](C:/dev/access2/docs/access2-stakeholder-demo-package-index.md).
4. If the feedback creates a V2 planning decision, update [access2-v2-checkpoint-and-roadmap.md](C:/dev/access2/docs/access2-v2-checkpoint-and-roadmap.md) or [access2-v2-planning.md](C:/dev/access2/docs/access2-v2-planning.md).
5. Keep future-scope requests separate from July must-fix items unless they directly block the July MVP story.
6. Do not convert stakeholder interest into implementation approval. Use a separate approved slice for any product, staging, mutation, PHI, CMS, claims, billing, EHR/FHIR, AI, or admin work.
