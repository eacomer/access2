"""
Dry-run validator for ACCESS2 external CSV intake.

This utility validates the July MVP controlled CSV template only. It performs no
database reads, no database writes, no network calls, and no imports from the
ACCESS2 application package.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REQUIRED_COLUMNS = (
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

OPTIONAL_COLUMNS = (
    "provider_npi",
    "organization_tin",
    "consent_status",
    "data_quality_flag",
    "source_file_batch_id",
)


class ExternalCsvIntakeValidationError(RuntimeError):
    """Raised when the CSV file cannot be read as an intake candidate."""


@dataclass(frozen=True, slots=True)
class RowValidationResult:
    row_number: int
    accepted: bool
    validation_errors: tuple[str, ...]
    external_record_id: str
    source_entity_name: str
    source_system: str
    source_file_batch_id: str


@dataclass(frozen=True, slots=True)
class CsvIntakeValidationReport:
    source_file_name: str
    row_count: int
    accepted_row_count: int
    rejected_row_count: int
    source_entity_names: tuple[str, ...]
    source_systems: tuple[str, ...]
    row_results: tuple[RowValidationResult, ...]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run validate an ACCESS2 external CSV intake file."
    )
    parser.add_argument("csv_path", help="Path to the CSV file to validate.")
    args = parser.parse_args(argv)

    try:
        report = validate_external_csv_intake(Path(args.csv_path))
    except ExternalCsvIntakeValidationError as exc:
        print(f"ACCESS2 external CSV intake dry-run failed: {exc}", file=sys.stderr)
        return 2

    print(format_report(report))
    return 1 if report.rejected_row_count else 0


def validate_external_csv_intake(csv_path: Path) -> CsvIntakeValidationReport:
    path = Path(csv_path)
    if not path.exists():
        raise ExternalCsvIntakeValidationError(f"file not found: {path}")
    if not path.is_file():
        raise ExternalCsvIntakeValidationError(f"path is not a file: {path}")

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = tuple(reader.fieldnames or ())
            if not fieldnames:
                raise ExternalCsvIntakeValidationError("CSV file is missing a header row.")

            rows = list(reader)
    except UnicodeDecodeError as exc:
        raise ExternalCsvIntakeValidationError("CSV file must be UTF-8 encoded.") from exc
    except csv.Error as exc:
        raise ExternalCsvIntakeValidationError(f"CSV parse error: {exc}") from exc

    missing_columns = tuple(column for column in REQUIRED_COLUMNS if column not in fieldnames)
    duplicate_scopes: dict[tuple[str, str, str], int] = {}
    row_results: list[RowValidationResult] = []

    for index, row in enumerate(rows, start=2):
        errors = list(_validate_row(row, missing_columns=missing_columns))
        external_record_id = _cell(row, "external_record_id")
        source_entity_name = _cell(row, "source_entity_name")
        source_system = _cell(row, "source_system")
        source_file_batch_id = _cell(row, "source_file_batch_id")

        if external_record_id:
            scope_value = source_file_batch_id or source_entity_name
            scope_type = "source_file_batch_id" if source_file_batch_id else "source_entity_name"
            if scope_value:
                duplicate_key = (scope_type, scope_value, external_record_id)
                first_row = duplicate_scopes.get(duplicate_key)
                if first_row is not None:
                    errors.append(
                        f"duplicate external_record_id within {scope_type}: first seen on row {first_row}"
                    )
                else:
                    duplicate_scopes[duplicate_key] = index

        row_results.append(
            RowValidationResult(
                row_number=index,
                accepted=not errors,
                validation_errors=tuple(errors),
                external_record_id=external_record_id,
                source_entity_name=source_entity_name,
                source_system=source_system,
                source_file_batch_id=source_file_batch_id,
            )
        )

    accepted_count = sum(1 for result in row_results if result.accepted)
    rejected_count = len(row_results) - accepted_count
    return CsvIntakeValidationReport(
        source_file_name=path.name,
        row_count=len(row_results),
        accepted_row_count=accepted_count,
        rejected_row_count=rejected_count,
        source_entity_names=_unique_non_empty(result.source_entity_name for result in row_results),
        source_systems=_unique_non_empty(result.source_system for result in row_results),
        row_results=tuple(row_results),
    )


def format_report(report: CsvIntakeValidationReport) -> str:
    lines = [
        "ACCESS2 external CSV intake dry-run report",
        f"- source file name: {report.source_file_name}",
        f"- row count: {report.row_count}",
        f"- accepted row count: {report.accepted_row_count}",
        f"- rejected row count: {report.rejected_row_count}",
        f"- source entity name(s): {_format_values(report.source_entity_names)}",
        f"- source system(s): {_format_values(report.source_systems)}",
        "- dry-run only: no database, network, or file write operations were performed",
    ]
    if report.rejected_row_count:
        lines.append("- rejected rows:")
        for result in report.row_results:
            if result.accepted:
                continue
            lines.append(f"  - row {result.row_number}:")
            lines.append(
                f"    external_record_id: {result.external_record_id or '[missing]'}"
            )
            lines.append(
                "    validation_errors: "
                + "; ".join(result.validation_errors)
            )
    else:
        lines.append("- validation summary: all rows accepted")
    return "\n".join(lines)


def _validate_row(row: dict[str, str | None], *, missing_columns: tuple[str, ...]) -> tuple[str, ...]:
    errors: list[str] = [f"missing required column: {column}" for column in missing_columns]

    for column in REQUIRED_COLUMNS:
        if column in missing_columns:
            continue
        if not _cell(row, column):
            errors.append(f"missing required field: {column}")

    patient_dob = _parse_date(_cell(row, "patient_dob"), "patient_dob")
    if patient_dob.error:
        errors.append(patient_dob.error)

    baseline_date = _parse_date(_cell(row, "baseline_date"), "baseline_date")
    if baseline_date.error:
        errors.append(baseline_date.error)

    current_value_date = _parse_date(_cell(row, "current_value_date"), "current_value_date")
    if current_value_date.error:
        errors.append(current_value_date.error)

    if baseline_date.value and current_value_date.value and baseline_date.value > current_value_date.value:
        errors.append("baseline_date must not be after current_value_date")

    return tuple(errors)


@dataclass(frozen=True, slots=True)
class ParsedDate:
    value: date | None
    error: str | None


def _parse_date(raw_value: str, column: str) -> ParsedDate:
    if not raw_value:
        return ParsedDate(value=None, error=None)
    try:
        parsed = date.fromisoformat(raw_value)
    except ValueError:
        return ParsedDate(value=None, error=f"{column} must use YYYY-MM-DD")
    if raw_value != parsed.isoformat():
        return ParsedDate(value=None, error=f"{column} must use YYYY-MM-DD")
    return ParsedDate(value=parsed, error=None)


def _cell(row: dict[str, str | None], column: str) -> str:
    return (row.get(column) or "").strip()


def _unique_non_empty(values) -> tuple[str, ...]:
    unique = {value for value in values if value}
    return tuple(sorted(unique))


def _format_values(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "[none]"


if __name__ == "__main__":
    raise SystemExit(main())
