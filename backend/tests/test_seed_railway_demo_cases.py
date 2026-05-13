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
from app.services.care_update_service import list_care_updates_for_patient
from app.services.intervention_task_service import list_tasks_for_patient
from app.services.outcome_service import list_outcomes_for_patient
from app.services.patient_signal_service import list_patient_escalations, list_patient_signals
from scripts.seed_railway_demo_cases import (
    DEMO_CASES,
    OVERRIDE_REASON,
    REJECTION_REASON,
    _get_or_create_admin,
    _get_or_create_org,
    seed_demo_cases,
)
from scripts.seed_local_v2_rejection_mutation import (
    ENABLE_ENV_VAR,
    LOCAL_REJECTION_EXTERNAL_PATIENT_ID,
    POST_REJECTION_CORRECTION_CARE_SUMMARY,
    POST_REJECTION_CORRECTION_OUTCOME_SOURCE,
    POST_REJECTION_CORRECTION_OUTCOME_VALUE,
    LocalMutationSeedGuardError,
    assert_local_mutation_seed_enabled,
    seed_local_v2_rejection_mutation_case,
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


def test_local_v2_rejection_mutation_seed_requires_explicit_guard() -> None:
    try:
        assert_local_mutation_seed_enabled(env={})
    except LocalMutationSeedGuardError as exc:
        assert f"{ENABLE_ENV_VAR}=true" in str(exc)
    else:
        raise AssertionError("Local V2 mutation seed guard allowed a missing opt-in.")


def test_local_v2_rejection_mutation_seed_blocks_production_like_urls() -> None:
    for key, value in (
        ("ACCESS2_E2E_BASE_URL", "https://access2.salvardata.com"),
        ("ACCESS2_E2E_API_BASE_URL", "https://api.salvardata.com/api/v1"),
        ("FRONTEND_ORIGIN", "https://access2-frontend-production-c029.up.railway.app"),
        ("API_BASE_URL", "https://example.railway.app/api/v1"),
        ("RAILWAY_PUBLIC_DOMAIN", "access2-backend-production-881f.up.railway.app"),
    ):
        try:
            assert_local_mutation_seed_enabled(
                env={
                    ENABLE_ENV_VAR: "true",
                    key: value,
                }
            )
        except LocalMutationSeedGuardError as exc:
            assert key in str(exc)
        else:
            raise AssertionError(f"Local V2 mutation seed guard allowed {key}={value}.")


def test_local_v2_rejection_mutation_seed_creates_pending_review_disposable_patient(
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setenv(ENABLE_ENV_VAR, "true")

    patient = seed_local_v2_rejection_mutation_case(db_session)
    organization = _get_or_create_org(db_session)
    admin = _get_or_create_admin(db_session, organization=organization)
    context = RequestContext(user=admin, organization=organization)
    audit_status = get_access_review_packet_patient_audit_status(
        db=db_session,
        context=context,
        patient=patient,
    )
    latest_snapshot = list_access_review_packet_snapshots(
        db=db_session,
        context=context,
        patient=patient,
        limit=1,
    )[0]

    assert patient.external_patient_id == LOCAL_REJECTION_EXTERNAL_PATIENT_ID
    assert not patient.external_patient_id.startswith("access2-railway-demo:")
    assert audit_status["review_status"] == "pending_review"
    assert audit_status["latest_snapshot_id"] == latest_snapshot.id
    assert latest_snapshot.review_status == AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW
    assert latest_snapshot.packet_json
    assert latest_snapshot.packet_markdown
    assert len(list_patient_signals(db=db_session, context=context, patient=patient)) >= 1
    assert len(list_patient_escalations(db=db_session, context=context, patient=patient)) >= 1
    assert any(
        task.status.value == "completed"
        for task in list_tasks_for_patient(db=db_session, context=context, patient=patient)
    )


def test_local_v2_rejection_mutation_seed_rerun_restores_latest_pending_review(
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setenv(ENABLE_ENV_VAR, "true")

    patient = seed_local_v2_rejection_mutation_case(db_session)
    organization = _get_or_create_org(db_session)
    admin = _get_or_create_admin(db_session, organization=organization)
    context = RequestContext(user=admin, organization=organization)
    first_snapshot = list_access_review_packet_snapshots(
        db=db_session,
        context=context,
        patient=patient,
        limit=1,
    )[0]
    first_packet_json = first_snapshot.packet_json
    first_packet_markdown = first_snapshot.packet_markdown

    assert POST_REJECTION_CORRECTION_CARE_SUMMARY not in first_packet_markdown
    assert "status=insufficient_data" in first_packet_markdown

    update_access_review_packet_snapshot_review(
        db=db_session,
        context=context,
        snapshot_id=first_snapshot.id,
        review_status=AccessReviewPacketSnapshotReviewStatus.REJECTED.value,
        review_note=None,
        decision_note="Synthetic local mutation test rejection reason.",
    )

    restored_patient = seed_local_v2_rejection_mutation_case(db_session)
    restored_status = get_access_review_packet_patient_audit_status(
        db=db_session,
        context=context,
        patient=restored_patient,
    )
    snapshots = list_access_review_packet_snapshots(
        db=db_session,
        context=context,
        patient=restored_patient,
        limit=2,
    )

    assert restored_patient.id == patient.id
    assert restored_status["review_status"] == "pending_review"
    assert snapshots[0].review_status == AccessReviewPacketSnapshotReviewStatus.PENDING_REVIEW
    assert snapshots[0].id != first_snapshot.id
    assert snapshots[1].review_status == AccessReviewPacketSnapshotReviewStatus.REJECTED
    assert snapshots[1].packet_json == first_packet_json
    assert snapshots[1].packet_markdown == first_packet_markdown
    assert POST_REJECTION_CORRECTION_CARE_SUMMARY in snapshots[0].packet_markdown
    assert "status=improved" in snapshots[0].packet_markdown
    assert POST_REJECTION_CORRECTION_CARE_SUMMARY not in snapshots[1].packet_markdown

    outcome_summaries = snapshots[0].packet_json["case_summary"]["outcome_summaries"]
    systolic_summary = next(
        item for item in outcome_summaries if item["metric_name"] == "systolic_bp"
    )
    assert systolic_summary["baseline"] == 132
    assert systolic_summary["latest"] == POST_REJECTION_CORRECTION_OUTCOME_VALUE
    assert systolic_summary["status"] == "improved"

    latest_care_update = snapshots[0].packet_json["case_summary"]["latest_care_update"]
    assert latest_care_update["summary"] == POST_REJECTION_CORRECTION_CARE_SUMMARY

    outcomes = list_outcomes_for_patient(db=db_session, context=context, patient=restored_patient)
    care_updates = list_care_updates_for_patient(
        db=db_session,
        context=context,
        patient=restored_patient,
    )
    assert any(outcome.source == POST_REJECTION_CORRECTION_OUTCOME_SOURCE for outcome in outcomes)
    assert any(update.summary == POST_REJECTION_CORRECTION_CARE_SUMMARY for update in care_updates)

    restored_again = seed_local_v2_rejection_mutation_case(db_session)
    snapshots_after_idempotent_rerun = list_access_review_packet_snapshots(
        db=db_session,
        context=context,
        patient=restored_again,
        limit=3,
    )
    outcomes_after_idempotent_rerun = list_outcomes_for_patient(
        db=db_session,
        context=context,
        patient=restored_again,
    )
    assert snapshots_after_idempotent_rerun[0].id == snapshots[0].id
    assert (
        sum(
            1
            for outcome in outcomes_after_idempotent_rerun
            if outcome.source == POST_REJECTION_CORRECTION_OUTCOME_SOURCE
        )
        == 1
    )


def test_local_v2_rejection_mutation_seed_does_not_change_railway_demo_cases(
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setenv(ENABLE_ENV_VAR, "true")

    seeded = seed_demo_cases(db_session)
    local_patient = seed_local_v2_rejection_mutation_case(db_session)
    seeded_again = seed_demo_cases(db_session)
    organization = _get_or_create_org(db_session)
    admin = _get_or_create_admin(db_session, organization=organization)
    context = RequestContext(user=admin, organization=organization)
    patient_3 = db_session.get(Patient, seeded_again[3])
    status_3 = get_access_review_packet_patient_audit_status(
        db=db_session,
        context=context,
        patient=patient_3,
    )

    assert seeded_again == seeded
    assert sorted(seeded_again) == [1, 2, 3, 4]
    assert local_patient.id not in set(seeded_again.values())
    assert local_patient.external_patient_id == LOCAL_REJECTION_EXTERNAL_PATIENT_ID
    assert status_3["review_status"] == "rejected"


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
