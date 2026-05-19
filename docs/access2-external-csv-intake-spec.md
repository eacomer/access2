# ACCESS2 External CSV Intake Specification

Date/checkpoint: May 19, 2026

## Purpose

This is a July MVP docs/spec artifact only. It does not authorize backend code, frontend code, database migrations, CSV importer implementation, staging work, or production mutation.

The purpose is to define a controlled external CSV intake path for provider, payor, or partner outcome records to enter the ACCESS2 proof chain using synthetic or explicitly approved pilot data. The July MVP intent is to show how externally supplied outcome and care evidence can become traceable review evidence, not to create an open upload platform or production healthcare integration.

This specification is not:

- Open public upload.
- Production PHI intake.
- FHIR/EHR integration.
- CMS production submission.
- Claims ingestion.
- Billing automation.
- AI feature.

FHIR-based exchange remains the future CMS-aligned integration direction. This CSV path is a bounded July MVP requirement/spec candidate only.

## Proof-Chain Mapping

```text
external source record → intake batch → validated row → patient/case candidate → outcome/evidence candidate → immutable review packet snapshot candidate → audit bundle handoff concept
```

The intake path should preserve traceability from the source record through validation and later review posture. Accepted rows should become eligible to support ACCESS2 outcome/evidence concepts only after validation. The audit handoff remains the same ACCESS2 posture: an approved latest review packet with `audit_bundle.available=true`.

## Required Columns

Each row must include these columns with non-empty values:

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

## Optional Columns

- `provider_npi`
- `organization_tin`
- `consent_status`
- `data_quality_flag`
- `source_file_batch_id`

## Row Validation Rules

- Required fields must be present and non-empty.
- Dates must use `YYYY-MM-DD`.
- `patient_dob` must be a valid date.
- `baseline_date` must not be after `current_value_date`.
- `baseline_value` and `current_value` must be parseable according to `measure_name` expectations, but the MVP must not overbuild measure logic.
- `source_entity_name` and `source_system` must be preserved with the accepted row.
- `external_record_id` plus `source_file_batch_id` or `source_entity_name` should be usable for duplicate detection conceptually.
- Rows with malformed required data are rejected, not partially imported.
- Rejected rows preserve `row_number` and `validation_errors`.

## Batch And Source Metadata

An intake batch should preserve these metadata fields:

- `source_file_name`
- `source_file_batch_id`
- `source_entity_name`
- `source_system`
- `imported_by_operator`
- `imported_at`
- `row_count`
- `accepted_row_count`
- `rejected_row_count`
- `validation_summary`

Batch metadata is part of the evidence chain. Operators should be able to explain where the row came from, who imported it, when validation happened, how many rows were accepted or rejected, and why rejected rows failed.

## Accepted-Row Mapping Into ACCESS2 Concepts

- `patient_external_id` maps to an external identity reference, not necessarily an internal ACCESS2 patient ID.
- `condition_track` maps to the chronic condition or program track.
- `measure_name`, `baseline_value`, `baseline_date`, `current_value`, and `current_value_date` map to outcome evidence.
- `patient_reported_outcome` and `evidence_note` map to evidence narrative.
- `intervention_summary` and `care_update_summary` map to care workflow notes.
- `source_entity_name`, `source_system`, `source_file_batch_id`, and `external_record_id` preserve source and batch traceability.
- Accepted rows should be eligible to create or support review packet candidates only after validation.

## Rejection Examples

Rows should be rejected with `row_number` and `validation_errors` when any of these occur:

- Missing `patient_external_id`.
- Invalid date format, such as `05/19/2026` instead of `2026-05-19`.
- `baseline_date` after `current_value_date`.
- Missing `measure_name`.
- Missing `source_system`.
- Duplicate `external_record_id` within the same batch.

Rejected rows should not create partial patient, outcome, evidence, care update, review packet, or audit-bundle state.

## Synthetic Sample CSV

```csv
external_record_id,source_entity_name,source_system,patient_external_id,patient_first_name,patient_last_name,patient_dob,condition_track,measure_name,baseline_value,baseline_date,current_value,current_value_date,patient_reported_outcome,intervention_summary,evidence_note,care_update_summary,provider_npi,organization_tin,consent_status,data_quality_flag,source_file_batch_id
SYN-REC-001,Synthetic Partner Clinic,partner_outcomes_csv,SYN-PAT-001,Alex,Sample,1968-04-12,hypertension,systolic_bp,156,2026-04-01,128,2026-05-15,"Reports fewer headaches and improved home BP readings","Medication adherence coaching and home BP monitoring completed","Synthetic BP log reviewed; current systolic value improved","Follow-up completed and outcome reviewed",1999999999,999999999,synthetic_only,validated,SYN-BATCH-20260519-A
SYN-REC-002,Synthetic Partner Clinic,partner_outcomes_csv,SYN-PAT-002,Jordan,Example,1974-09-03,diabetes,a1c,9.1,2026-03-20,7.4,2026-05-10,"Reports improved energy and consistent glucose checks","Nutrition coaching and medication review completed","Synthetic lab result shows A1C improvement","Care team reviewed updated outcome and documented next monitoring step",1999999999,999999999,synthetic_only,validated,SYN-BATCH-20260519-A
```

The sample is synthetic only. It must not be copied into real patient records or treated as PHI.

## Privacy And Compliance Guardrails

- No real PHI until compliance, security, and data-use approvals are complete.
- Synthetic or explicitly approved pilot data only.
- No secrets.
- No Medicare beneficiary IDs in the MVP template.
- No free-form file types in MVP.
- No open public upload workflow.
- No production mutation controls.
- No CMS production submission, claims ingestion, billing automation, FHIR/EHR integration, or AI feature work.

## Implementation Boundary

This specification does not authorize code changes yet. Future implementation should be small, controlled, operator-only, and tested locally first.

Any future implementation slice should:

- Keep intake behind explicit operator/admin controls.
- Validate all rows before accepting any row into workflow evidence.
- Preserve source and batch metadata.
- Report row-level acceptance and rejection.
- Use synthetic or explicitly approved pilot data only.
- Keep production V1 read-only until separate approval changes that posture.
- Avoid staging or non-local mutation unless isolated staging is explicitly approved.

## Recommended Next Implementation Slice

Recommended future slice: implement a local-only dry-run CSV intake validator that parses the strict template, validates rows, reports accepted/rejected counts, preserves row numbers and validation errors, and performs no database writes.

Do not implement that slice in this task. Do not add CSV upload/import code, database migrations, FHIR/EHR integration, CMS submission, claims ingestion, billing automation, staging mutation, production mutation, or AI features as part of this docs-only specification.
