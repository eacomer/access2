"""
Local-only V2 reviewer rejection mutation seed/reset.

This script is intentionally separate from the Railway demo seed. It creates or
repairs one disposable synthetic patient whose latest review packet snapshot is
pending_review, so local Playwright mutation tests can reject it repeatedly.
"""

from __future__ import annotations

import os
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.core.database import SessionLocal
from app.models.access_review_packet_snapshot import AccessReviewPacketSnapshotReviewStatus
from app.models.patient import Patient
from app.services.access_evidence_service import (
    create_access_review_packet_snapshot,
    get_access_review_packet_patient_audit_status,
    list_access_review_packet_snapshots,
)
from scripts.seed_railway_demo_cases import (
    DemoCase,
    _ensure_ready_workflow,
    _get_or_create_admin,
    _get_or_create_demo_patient,
    _get_or_create_org,
)


ENABLE_ENV_VAR = "ACCESS2_ENABLE_LOCAL_MUTATION_E2E"
LOCAL_REJECTION_EXTERNAL_PATIENT_ID = "access2-local-v2-mutation:reviewer-rejection"
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

    snapshot = _latest_pending_review_snapshot(db=db, context=context, patient=patient)
    if snapshot is None:
        snapshot = create_access_review_packet_snapshot(db=db, context=context, patient=patient)

    if not snapshot.packet_json or not snapshot.packet_markdown:
        raise RuntimeError(f"Local mutation snapshot {snapshot.id} is missing persisted packet content.")

    return patient


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


def _looks_like_configured_url_key(key: str) -> bool:
    normalized = key.upper()
    if normalized in {ENABLE_ENV_VAR, "PATH", "PYTHONPATH"}:
        return False
    return any(marker in normalized for marker in URL_ENV_NAME_MARKERS)


if __name__ == "__main__":
    main()
