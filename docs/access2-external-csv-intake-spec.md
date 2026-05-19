# ACCESS2 External CSV Intake Specification

Date/checkpoint: May 19, 2026

## Purpose

This began as a July MVP docs/spec artifact. The first approved implementation is a local-only dry-run validator at `backend/scripts/validate_external_csv_intake.py`; it performs no database writes, no database reads, no network calls, no frontend upload, no API endpoint, and no importer persistence.

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

Use [docs/examples/access2_external_csv_intake_valid_sample.csv](C:/dev/access2/docs/examples/access2_external_csv_intake_valid_sample.csv) as the local-only valid synthetic fixture for operator rehearsal.

```csv
external_record_id,source_entity_name,source_system,patient_external_id,patient_first_name,patient_last_name,patient_dob,condition_track,measure_name,baseline_value,baseline_date,current_value,current_value_date,patient_reported_outcome,intervention_summary,evidence_note,care_update_summary,provider_npi,organization_tin,consent_status,data_quality_flag,source_file_batch_id
SYN-REC-001,Synthetic Partner Clinic,partner_outcomes_csv,SYN-PAT-001,Alex,Sample,1968-04-12,hypertension,systolic_bp,156,2026-04-01,128,2026-05-15,"Reports fewer headaches and improved home BP readings","Medication adherence coaching and home BP monitoring completed","Synthetic BP log reviewed; current systolic value improved","Follow-up completed and outcome reviewed",1999999999,999999999,synthetic_only,validated,SYN-BATCH-20260519-A
SYN-REC-002,Synthetic Partner Clinic,partner_outcomes_csv,SYN-PAT-002,Jordan,Example,1974-09-03,diabetes,a1c,9.1,2026-03-20,7.4,2026-05-10,"Reports improved energy and consistent glucose checks","Nutrition coaching and medication review completed","Synthetic lab result shows A1C improvement","Care team reviewed updated outcome and documented next monitoring step",1999999999,999999999,synthetic_only,validated,SYN-BATCH-20260519-A
```

The sample is synthetic only. It must not be copied into real patient records or treated as PHI.

## Local Dry-Run Operator Example

Run the validator from PowerShell against the synthetic fixture:

```powershell
cd C:\dev\access2\backend
py -3 scripts\validate_external_csv_intake.py ..\docs\examples\access2_external_csv_intake_valid_sample.csv
```

Expected successful output shape:

```text
ACCESS2 external CSV intake dry-run report
- source file name: access2_external_csv_intake_valid_sample.csv
- row count: 2
- accepted row count: 2
- rejected row count: 0
- source entity name(s): Synthetic Partner Clinic
- source system(s): partner_outcomes_csv
- dry-run only: no database, network, or file write operations were performed
- validation summary: all rows accepted
```

Documented rejected-row example: if row 2 omits `source_system`, the dry run should reject the row, preserve `row_number=2`, report `missing required field: source_system`, and exit non-zero. The row must not create partial patient, outcome, evidence, review packet, audit bundle, or persisted importer state.

This dry run is local-only and no-write. It is not production PHI intake, CMS production submission, FHIR/EHR integration, claims ingestion, billing automation, or an open upload workflow.

## Operator Validation Checkpoint - May 19, 2026

Local-only rehearsal command:

```powershell
cd C:\dev\access2\backend
py -3 scripts\validate_external_csv_intake.py ..\docs\examples\access2_external_csv_intake_valid_sample.csv
```

Observed dry-run output:

```text
ACCESS2 external CSV intake dry-run report
- source file name: access2_external_csv_intake_valid_sample.csv
- row count: 2
- accepted row count: 2
- rejected row count: 0
- source entity name(s): Synthetic Partner Clinic
- source system(s): partner_outcomes_csv
- dry-run only: no database, network, or file write operations were performed
- validation summary: all rows accepted
```

Rehearsal confirmation:

- Row count: `2`.
- Accepted row count: `2`.
- Rejected row count: `0`.
- The dry-run report confirmed no database, network, or file-write operations.
- The fixture is synthetic demo data only and contains no real PHI.

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

This specification authorizes only the local dry-run validator already noted above. It does not authorize CSV upload/import persistence, API routes, frontend upload UI, database migrations, staging work, or production mutation. Future implementation should be small, controlled, operator-only, and tested locally first.

Local dry-run validator command shape:

```powershell
cd C:\dev\access2\backend
py -3 -m scripts.validate_external_csv_intake C:\path\to\synthetic-intake.csv
```

The validator prints the source file name, row count, accepted row count, rejected row count, source metadata, and row-level validation errors. It exits non-zero if any row is rejected.

Any future implementation slice should:

- Keep intake behind explicit operator/admin controls.
- Validate all rows before accepting any row into workflow evidence.
- Preserve source and batch metadata.
- Report row-level acceptance and rejection.
- Use synthetic or explicitly approved pilot data only.
- Keep production V1 read-only until separate approval changes that posture.
- Avoid staging or non-local mutation unless isolated staging is explicitly approved.

## Recommended Next Implementation Slice

Recommended future slice: add operator-facing dry-run examples and a sample synthetic CSV fixture for rehearsal, or extend the validator with a JSON report output if an operator workflow needs machine-readable validation results.

Do not add CSV upload/import code, database migrations, FHIR/EHR integration, CMS submission, claims ingestion, billing automation, staging mutation, production mutation, or AI features as part of that future slice unless explicitly approved.
