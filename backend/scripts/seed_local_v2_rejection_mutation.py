"""
Local-only V2 reviewer rejection mutation seed/reset.

This script is intentionally separate from the Railway demo seed. It creates or
repairs one disposable synthetic patient whose latest review packet snapshot is
pending_review, so local Playwright mutation tests can reject it repeatedly.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.core.database import SessionLocal
from app.models.access_review_packet_snapshot import AccessReviewPacketSnapshotReviewStatus
from app.models.care_update import CareUpdateType
from app.models.outcome import OutcomeType
from app.models.patient import Patient
from app.schemas.care_update import CareUpdateCreate
from app.schemas.outcome import OutcomeCreate
from app.services.access_evidence_service import (
    create_access_review_packet_snapshot,
    get_access_review_packet_patient_audit_status,
    list_access_review_packet_snapshots,
)
from app.services.care_update_service import create_care_update, list_care_updates_for_patient
from app.services.outcome_service import create_outcome, list_outcomes_for_patient
from scripts.seed_railway_demo_cases import (
    DemoCase,
    _ensure_ready_workflow,
    _get_or_create_admin,
    _get_or_create_demo_patient,
    _get_or_create_org,
)


ENABLE_ENV_VAR = "ACCESS2_ENABLE_LOCAL_MUTATION_E2E"
LOCAL_REJECTION_EXTERNAL_PATIENT_ID = "access2-local-v2-mutation:reviewer-rejection"
POST_REJECTION_CORRECTION_OUTCOME_SOURCE = "access2_local_v2_post_rejection_correction"
POST_REJECTION_CORRECTION_OUTCOME_VALUE = 124
POST_REJECTION_CORRECTION_CARE_SUMMARY = (
    "Post-rejection corrected evidence: synthetic systolic BP outcome improved after "
    "the completed intervention."
)
POST_REJECTION_CORRECTION_CARE_DETAILS = (
    "Synthetic local V2 correction evidence for disposable mutation testing. No real PHI."
)
PRODUCTION_HOST_MARKERS = (
    "access2.salvardata.com",
    "api.salvardata.com",
    "railway.app",
    "up.railway.app",
)
URL_ENV_NAME_MARKERS = (
    "URL",
    "URI",
    "ORIGIN",
    "HOST",
    "DOMAIN",
    "BASE",
)

LOCAL_REVIEWER_REJECTION_CASE = DemoCase(
    number=0,
    first_name="Local",
    last_name="V2 Rejection Mutation",
    external_patient_id=LOCAL_REJECTION_EXTERNAL_PATIENT_ID,
    sex="female",
    date_of_birth=date(1975, 5, 5),
)


class LocalMutationSeedGuardError(RuntimeError):
    """Raised when the local mutation seed is not explicitly allowed."""


def main() -> None:
    with SessionLocal() as db:
        patient = seed_local_v2_rejection_mutation_case(db)

    print("")
    print("Seeded ACCESS2 local V2 reviewer rejection mutation patient ID:")
    print(f"ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID={patient.id}")


def seed_local_v2_rejection_mutation_case(db: Session) -> Patient:
    assert_local_mutation_seed_enabled()

    organization = _get_or_create_org(db)
    admin = _get_or_create_admin(db, organization=organization)
    context = RequestContext(user=admin, organization=organization)

    patient = _get_or_create_demo_patient(
        db=db,
        context=context,
        case=LOCAL_REVIEWER_REJECTION_CASE,
    )
    _ensure_ready_workflow(
        db=db,
        context=context,
        patient=patient,
        outcome_value=132,
        care_summary="Synthetic local V2 reviewer rejection mutation case.",
        resolution_notes="Synthetic local escalation resolved before reviewer rejection mutation test.",
        resolve_with_evidence=True,
    )

    if _latest_review_status(db=db, context=context, patient=patient) == (
        AccessReviewPacketSnapshotReviewStatus.REJECTED.value
    ):
        _ensure_post_rejection_correction_evidence(db=db, context=context, patient=patient)

    snapshot = _latest_pending_review_snapshot(db=db, context=context, patient=patient)
    if snapshot is None:
        snapshot = create_access_review_packet_snapshot(db=db, context=context, patient=patient)

    if not snapshot.packet_json or not snapshot.packet_markdown:
        raise RuntimeError(f"Local mutation snapshot {snapshot.id} is missing persisted packet content.")

    return patient


def _ensure_post_rejection_correction_evidence(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
) -> None:
    outcomes = list_outcomes_for_patient(db=db, context=context, patient=patient)
    corrected_outcome = next(
        (
            item
            for item in outcomes
            if item.source == POST_REJECTION_CORRECTION_OUTCOME_SOURCE
            and item.metric_name == "systolic_bp"
        ),
        None,
    )
    base_outcome = next(
        (
            item
            for item in outcomes
            if item.metric_name == "systolic_bp" and item.intervention_task_id is not None
        ),
        None,
    )
    if base_outcome is None:
        return

    if corrected_outcome is None:
        corrected_outcome = create_outcome(
            db,
            context=context,
            payload=OutcomeCreate(
                patient_id=patient.id,
                intervention_task_id=base_outcome.intervention_task_id,
                signal_id=base_outcome.signal_id,
                type=OutcomeType.BP,
                metric_name="systolic_bp",
                value_numeric=POST_REJECTION_CORRECTION_OUTCOME_VALUE,
                unit="mmHg",
                observed_at=_after_latest_outcome(outcomes),
                source=POST_REJECTION_CORRECTION_OUTCOME_SOURCE,
            ),
        )

    care_updates = list_care_updates_for_patient(db=db, context=context, patient=patient)
    corrected_care_update = next(
        (item for item in care_updates if item.summary == POST_REJECTION_CORRECTION_CARE_SUMMARY),
        None,
    )
    if corrected_care_update is not None:
        return

    base_care_update = next(
        (item for item in care_updates if item.intervention_task_id == base_outcome.intervention_task_id),
        None,
    )
    create_care_update(
        db,
        context=context,
        payload=CareUpdateCreate(
            patient_id=patient.id,
            summary=POST_REJECTION_CORRECTION_CARE_SUMMARY,
            details=POST_REJECTION_CORRECTION_CARE_DETAILS,
            care_update_type=CareUpdateType.FOLLOW_UP,
            occurred_at=_after_latest_care_update(care_updates),
            escalation_id=base_care_update.escalation_id if base_care_update else None,
            intervention_task_id=base_outcome.intervention_task_id,
            outcome_id=corrected_outcome.id,
        ),
    )


def assert_local_mutation_seed_enabled(env: dict[str, str] | None = None) -> None:
    values = env if env is not None else os.environ
    if values.get(ENABLE_ENV_VAR, "").strip().lower() != "true":
        raise LocalMutationSeedGuardError(
            f"{ENABLE_ENV_VAR}=true is required to run the local mutation seed."
        )

    for key, raw_value in values.items():
        if not _looks_like_configured_url_key(key):
            continue
        value = raw_value.lower()
        for marker in PRODUCTION_HOST_MARKERS:
            if marker in value:
                raise LocalMutationSeedGuardError(
                    f"Refusing to run local mutation seed because {key} points to {marker}."
                )


def _latest_pending_review_snapshot(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
):
    snapshots = list_access_review_packet_snapshots(
        db=db,
        context=context,
        patient=patient,
        limit=1,
    )
    if not snapshots:
        return None
    audit_status = get_access_review_packet_patient_audit_status(
        db=db,
        context=context,
        patient=patient,
    )
    if audit_status["review_status"] == AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW.value:
        return snapshots[0]
    return None


def _latest_review_status(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
) -> str | None:
    audit_status = get_access_review_packet_patient_audit_status(
        db=db,
        context=context,
        patient=patient,
    )
    return audit_status["review_status"]


def _after_latest_outcome(outcomes) -> datetime:
    latest = max((item.observed_at for item in outcomes), default=None)
    if latest is None:
        return datetime.now(timezone.utc)
    return latest + timedelta(days=1)


def _after_latest_care_update(care_updates) -> datetime:
    latest = max((item.occurred_at for item in care_updates), default=None)
    if latest is None:
        return datetime.now(timezone.utc)
    return latest + timedelta(hours=1)


def _looks_like_configured_url_key(key: str) -> bool:
    normalized = key.upper()
    if normalized in {ENABLE_ENV_VAR, "PATH", "PYTHONPATH"}:
        return False
    return any(marker in normalized for marker in URL_ENV_NAME_MARKERS)


if __name__ == "__main__":
    main()
