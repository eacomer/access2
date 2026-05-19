# ACCESS2 July MVP Readiness Plan

Date/checkpoint: May 19, 2026

## Purpose

CMS ACCESS goes live in July 2026. ACCESS2 therefore needs a July MVP readiness plan that supports stakeholder walkthroughs, partner conversations, and controlled synthetic or explicitly approved pilot workflows.

The July goal is not to represent ACCESS2 as a fully mature production healthcare platform. The July goal is a credible ACCESS2 MVP and pilot-readiness package that shows how chronic-care evidence can move through review and audit-bundle posture while the higher-risk production controls remain explicitly gated.

## Readiness Boundaries

V1 production read-only demo readiness:

- Production frontend: `https://access2.salvardata.com`.
- Production backend API: `https://api.salvardata.com/api/v1`.
- Synthetic demo data only.
- Read-only evidence, audit-readiness, review-packet, audit-bundle, and manifest verification walkthrough.
- No production workflow mutation controls.

V2 localhost-only correction-loop proof:

- Localhost-only mutation proof using disposable synthetic local data.
- Shows assignment, rejection, preserved rejected snapshot history, corrected/new immutable snapshot creation, corrected approval, and `audit_bundle.available=true`.
- Does not authorize Railway, staging, production, `https://`, or non-loopback mutation targets.

July MVP/pilot-readiness target:

- ACCESS2 should be demo-ready and pilot-positioned by July.
- The July package should support stakeholder walkthroughs, partner conversations, and controlled synthetic or explicitly approved pilot workflows.
- The MVP posture should explain the onboarding-to-audit-bundle story and define the first bounded external data intake requirement.
- ACCESS2 should not be represented as fully production-ready for real PHI or live CMS reimbursement operations unless later compliance, security, data-use, and staging approvals occur.

Future fully production-user readiness:

- Requires production-grade mutation governance, security/compliance approval, data-use controls, operational support, isolated staging or preview validation, and production-safe reset/reseed ownership.
- Requires explicit approval before real PHI import, non-local mutation validation, FHIR/EHR integration, CMS production submission, claims ingestion, or billing automation.

## ACCESS2 Proof Chain

```text
signal → escalation → intervention → outcome → care update → resolution → evidence → immutable review packet snapshot → approval/rejection → audit bundle handoff
```

The July MVP should keep this chain visible and defensible. Any July scope should strengthen how evidence becomes reviewable, how review state is preserved, and how an approved packet reaches audit-bundle posture.

## July MVP Goal

ACCESS2 should be demo-ready and pilot-positioned by July 2026, not represented as fully production-ready for real PHI or live CMS reimbursement operations unless later compliance, security, data-use, and staging approvals occur.

The MVP should provide a credible operator story:

1. A patient record or partner-provided outcome record enters a controlled ACCESS2 workflow.
2. The record is validated and traceable to source/batch metadata.
3. Outcome and evidence posture becomes visible in the patient evidence chain.
4. An immutable review packet snapshot captures the reviewable evidence.
5. Review state determines whether the packet can proceed.
6. The handoff point is `audit_bundle.available=true` for the approved latest packet.

## July MVP In Scope

- Stable V1 production read-only stakeholder demo.
- Operator-repeatable V2 local correction-loop rehearsal.
- Documented onboarding-to-audit-bundle story.
- Controlled external CSV intake requirement, docs/spec only for now.
- Source and batch metadata preservation concept.
- Strict validation and rejection of malformed rows.
- Synthetic or explicitly approved pilot data only.
- Clear handoff point at `audit_bundle.available=true`.

## July MVP Out Of Scope

- Production mutation controls.
- Real PHI import unless compliance, security, and data-use approvals are complete.
- Full FHIR/EHR integration.
- CMS production submission.
- Claims ingestion.
- Billing automation.
- AI features.
- Broad UI redesign.
- Admin or override approval expansion.
- Isolated staging unless explicitly approved later.

## External Data Intake MVP Requirement

ACCESS2 will support a narrow, controlled external data intake path using a strict CSV template for synthetic or approved pilot records. The purpose is to demonstrate how provider, payor, or partner outcome records can enter the ACCESS2 proof chain and become reviewable evidence. The MVP import will validate required fields, preserve source/batch metadata, reject malformed rows, and map accepted rows into the patient outcome/evidence workflow.

This is not a full EHR/FHIR integration, not CMS production submission, not claims ingestion, and not approved for real PHI until compliance, security, and data-use controls are explicitly completed. FHIR-based exchange remains the future CMS-aligned integration path.

Use [access2-external-csv-intake-spec.md](C:/dev/access2/docs/access2-external-csv-intake-spec.md) for the controlled external CSV intake specification, including required columns, validation rules, batch/source metadata, accepted-row mapping, and rejection examples.

This requirement is a July MVP candidate/spec only until a separate implementation slice is approved. It should be treated as controlled operator/admin intake, not an open upload platform.

### Candidate CSV Template

Required fields:

- `external_record_id`
- `source_entity_name`
- `source_system`
- `patient_external_id`
- `patient_first_name`
- `patient_last_name`
- `patient_dob`
- `condition_track`
- `measure_name`
- `baseline_value`
- `baseline_date`
- `current_value`
- `current_value_date`
- `patient_reported_outcome`
- `intervention_summary`
- `evidence_note`
- `care_update_summary`

Optional fields:

- `provider_npi`
- `organization_tin`
- `consent_status`
- `data_quality_flag`
- `source_file_batch_id`

### CSV Intake Guardrails

- Accept synthetic data or explicitly approved pilot records only.
- Reject rows with missing required fields.
- Reject malformed dates, impossible numeric values, and unrecognized condition or measure names.
- Preserve the original `external_record_id`, `source_entity_name`, `source_system`, and `source_file_batch_id` for audit traceability.
- Preserve row-level acceptance/rejection status in operator-facing import results.
- Do not infer or generate clinical facts that are absent from the source row.
- Do not accept real PHI until compliance, security, and data-use controls are complete.

## July Definition Of Done

- V1 production read-only stakeholder walkthrough remains stable and validated.
- V2 localhost-only correction-loop rehearsal is operator-repeatable from the documented script.
- Stakeholder package explains what can be shown now, what can be pilot-positioned by July, and what remains future production hardening.
- External CSV intake is documented as a bounded MVP requirement/spec candidate with a strict template and validation expectations.
- Source/batch metadata preservation is defined as part of the intake requirement.
- July messaging clearly states that real PHI, production mutation, CMS production submission, claims ingestion, billing automation, and full FHIR/EHR integration are out of scope without later approvals.
- The audit-bundle handoff point remains `audit_bundle.available=true` for the approved latest packet.

## Risks And Guardrails

- Do not blur V1 production read-only demo readiness with production mutation readiness.
- Do not present localhost-only V2 mutation proof as production-enabled behavior.
- Do not accept real PHI without explicit compliance, security, and data-use approvals.
- Do not build CSV importer code until a separate implementation slice is approved.
- Do not build FHIR, EHR integration, CMS submission, claims ingestion, billing automation, AI features, or override approval as part of the July MVP plan.
- Keep staging deferred until isolated staging or preview infrastructure is explicitly approved.
- Keep rejected, approved, and historical review packet snapshots immutable.
- Keep the July story anchored to evidence, review, and audit-bundle handoff rather than broad platform expansion.

## Recommended Next Slice

The first approved implementation is a local-only dry-run CSV intake validator for the strict template in [access2-external-csv-intake-spec.md](C:/dev/access2/docs/access2-external-csv-intake-spec.md). It performs no database writes, no database reads, no network calls, no frontend upload, no API endpoint, and no importer persistence.

Operator rehearsal can use the synthetic fixture at [docs/examples/access2_external_csv_intake_valid_sample.csv](C:/dev/access2/docs/examples/access2_external_csv_intake_valid_sample.csv) with the PowerShell command documented in the CSV intake specification.

Recommended next slice: use the documented dry-run fixture in a local operator rehearsal, or add a JSON report option if a machine-readable dry-run result is needed.

Do not implement CSV upload/import persistence, FHIR/EHR integration, CMS submission, claims ingestion, billing automation, staging mutation, or production mutation until a separate implementation slice is approved.
