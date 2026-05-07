from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.access_review_packet_snapshot import AccessReviewPacketSnapshotReviewStatus
from app.models.patient import Patient
from app.services.access_evidence_service import (
    get_access_review_packet_patient_audit_status,
    get_access_review_packet_snapshot_audit_bundle,
    list_access_review_packet_snapshots,
    update_access_review_packet_snapshot_review,
    verify_access_review_packet_snapshot_audit_manifest,
)
from app.services.intervention_task_service import list_tasks_for_patient
from app.services.patient_signal_service import list_patient_escalations, list_patient_signals
from scripts.seed_railway_demo_cases import (
    DEMO_CASES,
    OVERRIDE_REASON,
    REJECTION_REASON,
    _get_or_create_admin,
    _get_or_create_org,
    seed_demo_cases,
)


def test_seed_railway_demo_cases_is_idempotent_and_printable(db_session: Session) -> None:
    first = seed_demo_cases(db_session)
    second = seed_demo_cases(db_session)

    assert first == second
    assert sorted(first) == [1, 2, 3, 4]

    for case_number, patient_id in second.items():
        patient = db_session.get(Patient, patient_id)
        assert patient is not None
        assert patient.external_patient_id == DEMO_CASES[case_number].external_patient_id
        assert patient.first_name == "Demo"


def test_seed_railway_demo_case_audit_postures(db_session: Session) -> None:
    seeded = seed_demo_cases(db_session)
    organization = _get_or_create_org(db_session)
    admin = _get_or_create_admin(db_session, organization=organization)
    context = RequestContext(user=admin, organization=organization)

    patient_1 = db_session.get(Patient, seeded[1])
    status_1 = get_access_review_packet_patient_audit_status(
        db=db_session,
        context=context,
        patient=patient_1,
    )
    assert status_1["review_status"] == "approved"
    assert status_1["completion_summary"]["status"] == "audit_ready"
    assert status_1["completion_summary"]["has_required_evidence"] is True
    assert status_1["audit_bundle"]["available"] is True
    assert status_1["audit_bundle"]["exported"] is True
    assert _manifest_verifies(db_session, context, status_1["latest_snapshot_id"])

    patient_2 = db_session.get(Patient, seeded[2])
    status_2 = get_access_review_packet_patient_audit_status(
        db=db_session,
        context=context,
        patient=patient_2,
    )
    assert status_2["review_status"] == "pending_review"
    assert status_2["completion_summary"]["status"] == "incomplete"
    assert status_2["completion_summary"]["has_required_evidence"] is False
    assert status_2["next_step"]["action"] == "complete_missing_evidence"
    assert len(list_patient_signals(db=db_session, context=context, patient=patient_2)) >= 1
    assert len(list_patient_escalations(db=db_session, context=context, patient=patient_2)) >= 1
    assert any(
        task.status.value == "in_progress"
        for task in list_tasks_for_patient(db=db_session, context=context, patient=patient_2)
    )
    assert _normal_approval_is_blocked(db_session, context, status_2["latest_snapshot_id"])

    patient_3 = db_session.get(Patient, seeded[3])
    status_3 = get_access_review_packet_patient_audit_status(
        db=db_session,
        context=context,
        patient=patient_3,
    )
    assert status_3["review_status"] == "rejected"
    assert status_3["next_step"]["action"] == "create_snapshot"
    snapshot_3 = list_access_review_packet_snapshots(
        db=db_session,
        context=context,
        patient=patient_3,
        limit=1,
    )[0]
    assert snapshot_3.review_note == REJECTION_REASON

    patient_4 = db_session.get(Patient, seeded[4])
    status_4 = get_access_review_packet_patient_audit_status(
        db=db_session,
        context=context,
        patient=patient_4,
    )
    assert status_4["review_status"] == "approved"
    assert status_4["review_state"]["state"] == "approved_with_override"
    assert status_4["review_state"]["approval_override_used"] is True
    assert status_4["review_state"]["missing_checklist_items"]
    assert status_4["audit_bundle"]["available"] is True
    snapshot_4 = list_access_review_packet_snapshots(
        db=db_session,
        context=context,
        patient=patient_4,
        limit=1,
    )[0]
    assert snapshot_4.review_note == OVERRIDE_REASON
    bundle_4 = get_access_review_packet_snapshot_audit_bundle(
        db=db_session,
        context=context,
        snapshot_id=snapshot_4.id,
    )
    assert bundle_4["audit_manifest"]["approval_override_used"] is True
    assert _manifest_verifies(db_session, context, snapshot_4.id)


def _normal_approval_is_blocked(db: Session, context: RequestContext, snapshot_id) -> bool:
    try:
        update_access_review_packet_snapshot_review(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
            review_status=AccessReviewPacketSnapshotReviewStatus.APPROVED.value,
            review_note="Should block.",
        )
    except Exception as exc:
        db.rollback()
        return "missing review_checklist" in str(exc) or "missing items" in str(exc)
    return False


def _manifest_verifies(db: Session, context: RequestContext, snapshot_id) -> bool:
    bundle = get_access_review_packet_snapshot_audit_bundle(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    result = verify_access_review_packet_snapshot_audit_manifest(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
        submitted_manifest=bundle["audit_manifest"],
    )
    return bool(result and result["verified"])
