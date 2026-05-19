from __future__ import annotations

import ast
import csv
from pathlib import Path

from scripts.validate_external_csv_intake import (
    REQUIRED_COLUMNS,
    format_report,
    main,
    validate_external_csv_intake,
)


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_external_csv_intake.py"


def valid_row(**overrides: str) -> dict[str, str]:
    row = {
        "external_record_id": "SYN-REC-001",
        "source_entity_name": "Synthetic Partner Clinic",
        "source_system": "partner_outcomes_csv",
        "patient_external_id": "SYN-PAT-001",
        "patient_first_name": "Alex",
        "patient_last_name": "Sample",
        "patient_dob": "1968-04-12",
        "condition_track": "hypertension",
        "measure_name": "systolic_bp",
        "baseline_value": "156",
        "baseline_date": "2026-04-01",
        "current_value": "128",
        "current_value_date": "2026-05-15",
        "patient_reported_outcome": "Reports improved home readings.",
        "intervention_summary": "Medication adherence coaching completed.",
        "evidence_note": "Synthetic BP log reviewed.",
        "care_update_summary": "Follow-up completed and outcome reviewed.",
        "provider_npi": "1999999999",
        "organization_tin": "999999999",
        "consent_status": "synthetic_only",
        "data_quality_flag": "validated",
        "source_file_batch_id": "SYN-BATCH-20260519-A",
    }
    row.update(overrides)
    return row


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> Path:
    resolved_fieldnames = fieldnames or list(valid_row().keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=resolved_fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in resolved_fieldnames})
    return path


def assert_single_rejection(path: Path, expected: str) -> None:
    report = validate_external_csv_intake(path)

    assert report.row_count == 1
    assert report.accepted_row_count == 0
    assert report.rejected_row_count == 1
    assert expected in "; ".join(report.row_results[0].validation_errors)


def test_valid_synthetic_csv_is_accepted(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "valid.csv", [valid_row()])

    report = validate_external_csv_intake(path)

    assert report.source_file_name == "valid.csv"
    assert report.row_count == 1
    assert report.accepted_row_count == 1
    assert report.rejected_row_count == 0
    assert report.source_entity_names == ("Synthetic Partner Clinic",)
    assert report.source_systems == ("partner_outcomes_csv",)
    assert "all rows accepted" in format_report(report)


def test_missing_required_field_is_rejected(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "missing-patient.csv", [valid_row(patient_external_id="")])

    assert_single_rejection(path, "missing required field: patient_external_id")


def test_invalid_date_format_is_rejected(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "bad-date.csv", [valid_row(current_value_date="05/15/2026")])

    assert_single_rejection(path, "current_value_date must use YYYY-MM-DD")


def test_baseline_date_after_current_value_date_is_rejected(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "date-order.csv",
        [valid_row(baseline_date="2026-05-16", current_value_date="2026-05-15")],
    )

    assert_single_rejection(path, "baseline_date must not be after current_value_date")


def test_duplicate_external_record_id_in_same_batch_is_rejected(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "duplicate.csv",
        [
            valid_row(external_record_id="SYN-DUP-001", patient_external_id="SYN-PAT-001"),
            valid_row(external_record_id="SYN-DUP-001", patient_external_id="SYN-PAT-002"),
        ],
    )

    report = validate_external_csv_intake(path)

    assert report.row_count == 2
    assert report.accepted_row_count == 1
    assert report.rejected_row_count == 1
    assert report.row_results[1].row_number == 3
    assert "duplicate external_record_id within source_file_batch_id" in "; ".join(
        report.row_results[1].validation_errors
    )


def test_duplicate_external_record_id_uses_source_when_batch_is_missing(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "duplicate-source.csv",
        [
            valid_row(
                external_record_id="SYN-DUP-002",
                patient_external_id="SYN-PAT-001",
                source_file_batch_id="",
            ),
            valid_row(
                external_record_id="SYN-DUP-002",
                patient_external_id="SYN-PAT-002",
                source_file_batch_id="",
            ),
        ],
    )

    report = validate_external_csv_intake(path)

    assert report.accepted_row_count == 1
    assert report.rejected_row_count == 1
    assert "duplicate external_record_id within source_entity_name" in "; ".join(
        report.row_results[1].validation_errors
    )


def test_missing_source_system_is_rejected(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "missing-source-system.csv", [valid_row(source_system="")])

    assert_single_rejection(path, "missing required field: source_system")


def test_missing_required_column_is_rejected(tmp_path: Path) -> None:
    fieldnames = [field for field in valid_row().keys() if field != "measure_name"]
    path = write_csv(tmp_path / "missing-column.csv", [valid_row()], fieldnames=fieldnames)

    assert_single_rejection(path, "missing required column: measure_name")


def test_main_prints_report_and_exits_nonzero_for_rejected_rows(tmp_path: Path, capsys) -> None:
    path = write_csv(tmp_path / "cli-rejected.csv", [valid_row(source_system="")])

    exit_code = main([str(path)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "ACCESS2 external CSV intake dry-run report" in output
    assert "- source file name: cli-rejected.csv" in output
    assert "- rejected row count: 1" in output
    assert "row 2" in output
    assert "missing required field: source_system" in output
    assert "no database, network, or file write operations were performed" in output


def test_validator_script_imports_no_app_db_or_network_modules() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])

    assert "app" not in imported_modules
    assert "sqlalchemy" not in imported_modules
    assert "requests" not in imported_modules
    assert "httpx" not in imported_modules
    assert "socket" not in imported_modules


def test_required_columns_match_spec() -> None:
    assert REQUIRED_COLUMNS == (
        "external_record_id",
        "source_entity_name",
        "source_system",
        "patient_external_id",
        "patient_first_name",
        "patient_last_name",
        "patient_dob",
        "condition_track",
        "measure_name",
        "baseline_value",
        "baseline_date",
        "current_value",
        "current_value_date",
        "patient_reported_outcome",
        "intervention_summary",
        "evidence_note",
        "care_update_summary",
    )
