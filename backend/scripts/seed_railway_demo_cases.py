"""
One-time synthetic ACCESS2 Railway demo-case seed.

Safe to re-run: the script finds demo patients by stable synthetic
external_patient_id markers, creates missing workflow evidence, and creates a
new immutable review snapshot only when the latest snapshot does not match the
required demo posture. It does not delete unrelated data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.access_review_packet_snapshot import AccessReviewPacketSnapshotReviewStatus
from app.models.care_update import CareUpdateType
from app.models.intervention_task import InterventionTaskStatus
from app.models.organization import Organization
from app.models.outcome import OutcomeType
from app.models.patient import Patient
from app.models.patient_signal import (
    EscalationResolutionReason,
    EscalationStatus,
    PatientEscalation,
    PatientSignal,
    SignalType,
)
from app.models.user import User
from app.schemas.care_update import CareUpdateCreate
from app.schemas.outcome import OutcomeCreate
from app.schemas.patient import PatientCreate
from app.schemas.signal import PatientSignalCreate
from app.schemas.task import InterventionTaskCreate
from app.services.access_evidence_service import (
    AccessReviewPacketApprovalBlockedError,
    build_access_review_packet_snapshot_export_metadata,
    create_access_review_packet_snapshot,
    get_access_review_packet_patient_audit_status,
    get_access_review_packet_snapshot_audit_bundle,
    list_access_review_packet_snapshot_events,
    list_access_review_packet_snapshots,
    record_access_review_packet_snapshot_audit_bundle_export,
    update_access_review_packet_snapshot_review,
    verify_access_review_packet_snapshot_audit_manifest,
)
from app.services.care_update_service import create_care_update, list_care_updates_for_patient
from app.services.intervention_task_service import (
    complete_task,
    create_task_from_escalation,
    list_tasks_for_patient,
    start_task,
)
from app.services.outcome_service import create_outcome, list_outcomes_for_patient
from app.services.patient_service import DuplicatePatientRecordError, create_patient
from app.services.patient_signal_service import (
    create_patient_signal,
    list_patient_escalations,
    list_patient_signals,
    resolve_escalation,
    transition_escalation_status,
)


ORG_SLUG = "access2-demo"
ORG_NAME = "ACCESS2 Demo Organization"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"

REJECTION_REASON = (
    "Outcome documentation does not clearly connect intervention to measurable improvement."
)
OVERRIDE_REASON = (
    "Approved for demo exception: source documentation exists outside the synthetic dataset "
    "and will be reconciled before production use."
)


@dataclass(frozen=True, slots=True)
class DemoCase:
    number: int
    first_name: str
    last_name: str
    external_patient_id: str
    sex: str
    date_of_birth: date

    @property
    def env_name(self) -> str:
        return f"ACCESS2_E2E_DEMO_PATIENT_{self.number}_ID"


DEMO_CASES = {
    1: DemoCase(
        number=1,
        first_name="Demo",
        last_name="Patient 1 - Audit Ready",
        external_patient_id="access2-railway-demo:patient-1:audit-ready",
        sex="female",
        date_of_birth=date(1971, 1, 1),
    ),
    2: DemoCase(
        number=2,
        first_name="Demo",
        last_name="Patient 2 - Missing Evidence",
        external_patient_id="access2-railway-demo:patient-2:missing-evidence",
        sex="male",
        date_of_birth=date(1972, 2, 2),
    ),
    3: DemoCase(
        number=3,
        first_name="Demo",
        last_name="Patient 3 - Rejected Review",
        external_patient_id="access2-railway-demo:patient-3:rejected-review",
        sex="female",
        date_of_birth=date(1973, 3, 3),
    ),
    4: DemoCase(
        number=4,
        first_name="Demo",
        last_name="Patient 4 - Override Approval",
        external_patient_id="access2-railway-demo:patient-4:override-approval",
        sex="male",
        date_of_birth=date(1974, 4, 4),
    ),
}


def main() -> None:
    with SessionLocal() as db:
        seeded = seed_demo_cases(db)

    print("")
    print("Seeded ACCESS2 Railway demo patient IDs:")
    for case_number in sorted(seeded):
        print(f"{DEMO_CASES[case_number].env_name}={seeded[case_number]}")


def seed_demo_cases(db: Session) -> dict[int, UUID]:
    organization = _get_or_create_org(db)
    admin = _get_or_create_admin(db, organization=organization)
    context = RequestContext(user=admin, organization=organization)

    patient_1 = _seed_patient_1_audit_ready(db=db, context=context)
    patient_2 = _seed_patient_2_missing_evidence(db=db, context=context)
    patient_3 = _seed_patient_3_rejected_review(db=db, context=context)
    patient_4 = _seed_patient_4_override_approval(db=db, context=context)

    return {
        1: patient_1.id,
        2: patient_2.id,
        3: patient_3.id,
        4: patient_4.id,
    }


def _seed_patient_1_audit_ready(*, db: Session, context: RequestContext) -> Patient:
    patient = _get_or_create_demo_patient(db=db, context=context, case=DEMO_CASES[1])
    workflow = _ensure_ready_workflow(
        db=db,
        context=context,
        patient=patient,
        outcome_value=124,
        care_summary="Synthetic BP improvement documented after outreach.",
        resolution_notes="Synthetic escalation resolved after measured BP improvement.",
        resolve_with_evidence=True,
    )
    _ensure_task_completed(db=db, context=context, task=workflow["task"])
    snapshot = _latest_matching_snapshot(
        db=db,
        context=context,
        patient=patient,
        predicate=lambda audit_status: (
            audit_status["review_status"] == "approved"
            and audit_status["completion_summary"]["has_required_evidence"]
            and audit_status["audit_bundle"]["available"]
        ),
    )
    if snapshot is None:
        snapshot = create_access_review_packet_snapshot(db=db, context=context, patient=patient)
        update_access_review_packet_snapshot_review(
            db=db,
            context=context,
            snapshot_id=snapshot.id,
            review_status="approved",
            review_note="Synthetic audit-ready packet approved for Railway demo.",
            decision_note="Synthetic audit-ready packet approved for Railway demo.",
        )
    _ensure_json_export_recorded(db=db, context=context, snapshot_id=snapshot.id)
    _assert_manifest_verifies(db=db, context=context, snapshot_id=snapshot.id)
    return patient


def _seed_patient_2_missing_evidence(*, db: Session, context: RequestContext) -> Patient:
    patient = _get_or_create_demo_patient(db=db, context=context, case=DEMO_CASES[2])
    workflow = _ensure_signal_escalation_task(
        db=db,
        context=context,
        patient=patient,
        signal_value=9.6,
        task_title="Start synthetic outreach without outcome evidence",
    )
    _ensure_task_started(db=db, context=context, task=workflow["task"])
    snapshot = _latest_matching_snapshot(
        db=db,
        context=context,
        patient=patient,
        predicate=lambda audit_status: (
            audit_status["review_status"] == "pending_review"
            and not audit_status["completion_summary"]["has_required_evidence"]
            and audit_status["completion_summary"]["missing_evidence_count"] > 0
        ),
    )
    if snapshot is None:
        snapshot = create_access_review_packet_snapshot(db=db, context=context, patient=patient)
    _assert_normal_approval_blocked(db=db, context=context, snapshot_id=snapshot.id)
    return patient


def _seed_patient_3_rejected_review(*, db: Session, context: RequestContext) -> Patient:
    patient = _get_or_create_demo_patient(db=db, context=context, case=DEMO_CASES[3])
    _ensure_ready_workflow(
        db=db,
        context=context,
        patient=patient,
        outcome_value=138,
        care_summary="Synthetic reviewer found causal documentation too weak.",
        resolution_notes="Synthetic escalation closure prepared for rejected-review demo.",
        resolve_with_evidence=True,
    )
    snapshot = _latest_matching_snapshot(
        db=db,
        context=context,
        patient=patient,
        predicate=lambda audit_status: (
            audit_status["review_status"] == "rejected"
            and audit_status["next_step"]["action"] == "create_snapshot"
        ),
    )
    if snapshot is None:
        snapshot = create_access_review_packet_snapshot(db=db, context=context, patient=patient)
        update_access_review_packet_snapshot_review(
            db=db,
            context=context,
            snapshot_id=snapshot.id,
            review_status="rejected",
            review_note=REJECTION_REASON,
            decision_note=REJECTION_REASON,
        )
    return patient


def _seed_patient_4_override_approval(*, db: Session, context: RequestContext) -> Patient:
    patient = _get_or_create_demo_patient(db=db, context=context, case=DEMO_CASES[4])
    _ensure_ready_workflow(
        db=db,
        context=context,
        patient=patient,
        outcome_value=130,
        care_summary="Synthetic source documentation exists outside the seeded dataset.",
        resolution_notes="Synthetic escalation resolved from external source documentation.",
        resolve_with_evidence=False,
    )
    snapshot = _latest_matching_snapshot(
        db=db,
        context=context,
        patient=patient,
        predicate=lambda audit_status: (
            audit_status["review_status"] == "approved"
            and audit_status["review_state"] is not None
            and audit_status["review_state"]["approval_override_used"]
        ),
    )
    if snapshot is None:
        snapshot = create_access_review_packet_snapshot(db=db, context=context, patient=patient)
        _assert_normal_approval_blocked(db=db, context=context, snapshot_id=snapshot.id)
        update_access_review_packet_snapshot_review(
            db=db,
            context=context,
            snapshot_id=snapshot.id,
            review_status="approved",
            review_note=OVERRIDE_REASON,
            decision_note=OVERRIDE_REASON,
            override_missing_checklist=True,
            override_reason=OVERRIDE_REASON,
        )
    _ensure_json_export_recorded(db=db, context=context, snapshot_id=snapshot.id)
    _assert_manifest_verifies(db=db, context=context, snapshot_id=snapshot.id)
    return patient


def _get_or_create_org(db: Session) -> Organization:
    organization = db.execute(
        select(Organization).where(Organization.slug == ORG_SLUG)
    ).scalar_one_or_none()
    if organization is not None:
        print(f"FOUND org: {ORG_SLUG}")
        return organization

    organization = Organization(name=ORG_NAME, slug=ORG_SLUG)
    db.add(organization)
    db.commit()
    db.refresh(organization)
    print(f"CREATED org: {ORG_SLUG}")
    return organization


def _get_or_create_admin(db: Session, *, organization: Organization) -> User:
    user = db.execute(select(User).where(User.email == ADMIN_EMAIL)).scalar_one_or_none()
    if user is not None:
        changed = False
        if user.organization_id != organization.id:
            user.organization_id = organization.id
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        if changed:
            db.add(user)
            db.commit()
            db.refresh(user)
        print(f"FOUND admin user: {ADMIN_EMAIL}")
        return user

    user = User(
        email=ADMIN_EMAIL,
        full_name="Admin User",
        hashed_password=get_password_hash(ADMIN_PASSWORD),
        is_active=True,
        is_superuser=True,
        organization_id=organization.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"CREATED admin user: {ADMIN_EMAIL}")
    return user


def _get_or_create_demo_patient(
    *,
    db: Session,
    context: RequestContext,
    case: DemoCase,
) -> Patient:
    patient = db.execute(
        select(Patient).where(
            Patient.organization_id == context.organization_id,
            Patient.external_patient_id == case.external_patient_id,
        )
    ).scalar_one_or_none()
    if patient is not None:
        changed = False
        for field_name, expected in (
            ("first_name", case.first_name),
            ("last_name", case.last_name),
            ("date_of_birth", case.date_of_birth),
            ("sex", case.sex),
            ("is_active", True),
        ):
            if getattr(patient, field_name) != expected:
                setattr(patient, field_name, expected)
                changed = True
        if changed:
            db.add(patient)
            db.commit()
            db.refresh(patient)
        print(f"FOUND demo patient {case.number}: {patient.id}")
        return patient

    try:
        patient = create_patient(
            db,
            context=context,
            payload=PatientCreate(
                first_name=case.first_name,
                last_name=case.last_name,
                date_of_birth=case.date_of_birth,
                sex=case.sex,
                external_patient_id=case.external_patient_id,
            ),
        )
    except DuplicatePatientRecordError:
        patient = db.execute(
            select(Patient).where(
                Patient.organization_id == context.organization_id,
                Patient.first_name == case.first_name,
                Patient.last_name == case.last_name,
                Patient.date_of_birth == case.date_of_birth,
            )
        ).scalar_one()
        patient.external_patient_id = case.external_patient_id
        patient.is_active = True
        db.add(patient)
        db.commit()
        db.refresh(patient)
    print(f"CREATED demo patient {case.number}: {patient.id}")
    return patient


def _ensure_ready_workflow(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
    outcome_value: float,
    care_summary: str,
    resolution_notes: str,
    resolve_with_evidence: bool,
) -> dict[str, object]:
    workflow = _ensure_signal_escalation_task(
        db=db,
        context=context,
        patient=patient,
        signal_value=9.4,
        task_title="Complete synthetic intervention workflow",
    )
    escalation = workflow["escalation"]
    task = workflow["task"]
    _ensure_task_completed(db=db, context=context, task=task)
    outcome = _ensure_outcome(
        db=db,
        context=context,
        patient=patient,
        task_id=task.id,
        signal_id=workflow["signal"].id,
        value_numeric=outcome_value,
    )
    care_update = _ensure_care_update(
        db=db,
        context=context,
        patient=patient,
        escalation_id=escalation.id,
        task_id=task.id,
        outcome_id=outcome.id,
        summary=care_summary,
    )
    if escalation.status != EscalationStatus.RESOLVED:
        resolve_escalation(
            db=db,
            context=context,
            escalation=escalation,
            resolution_reason=EscalationResolutionReason.ISSUE_ADDRESSED,
            resolution_notes=resolution_notes,
            outcome_id=outcome.id if resolve_with_evidence else None,
            care_update_id=care_update.id if resolve_with_evidence else None,
            resolved_at=_now() + timedelta(hours=2),
        )
    return {
        **workflow,
        "outcome": outcome,
        "care_update": care_update,
    }


def _ensure_signal_escalation_task(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
    signal_value: float,
    task_title: str,
) -> dict[str, object]:
    signals = list_patient_signals(db=db, context=context, patient=patient)
    signal = next((item for item in signals if item.signal_type == SignalType.SYMPTOM_SCORE), None)
    escalation = None
    if signal is not None:
        escalation = db.execute(
            select(PatientEscalation).where(PatientEscalation.signal_id == signal.id)
        ).scalar_one_or_none()
    if signal is None or escalation is None:
        signal, escalation = create_patient_signal(
            db,
            context=context,
            patient=patient,
            payload=PatientSignalCreate(
                signal_type=SignalType.SYMPTOM_SCORE,
                signal_source="railway_demo_seed",
                signal_value_numeric=signal_value,
                unit="score",
                recorded_at=_now() - timedelta(days=4),
                notes="Synthetic Railway demo signal. No real PHI.",
                escalation_sla_due_at=_now() - timedelta(days=2),
            ),
        )
    if escalation is None:
        raise RuntimeError(f"Synthetic signal did not create escalation for patient {patient.id}")

    tasks = list_tasks_for_patient(db=db, context=context, patient=patient)
    task = next((item for item in tasks if item.escalation_id == escalation.id), None)
    if task is None:
        task = create_task_from_escalation(
            db,
            context=context,
            escalation=escalation,
            payload=InterventionTaskCreate(
                title=task_title,
                description="Synthetic Railway demo intervention task. No real PHI.",
                priority="high",
                due_at=_now() - timedelta(days=1),
                assigned_user_id=context.user.id,
            ),
        )

    return {"signal": signal, "escalation": escalation, "task": task}


def _ensure_task_started(*, db: Session, context: RequestContext, task) -> None:
    if task.status == InterventionTaskStatus.OPEN:
        start_task(db=db, context=context, task=task)


def _ensure_task_completed(*, db: Session, context: RequestContext, task) -> None:
    if task.status == InterventionTaskStatus.OPEN:
        task = start_task(db=db, context=context, task=task)
    if task.status != InterventionTaskStatus.COMPLETED:
        complete_task(
            db=db,
            context=context,
            task=task,
            completion_note="Synthetic intervention completed for Railway demo.",
        )


def _ensure_outcome(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
    task_id: UUID,
    signal_id: UUID,
    value_numeric: float,
):
    outcomes = list_outcomes_for_patient(db=db, context=context, patient=patient)
    outcome = next((item for item in outcomes if item.intervention_task_id == task_id), None)
    if outcome is not None:
        return outcome
    return create_outcome(
        db,
        context=context,
        payload=OutcomeCreate(
            patient_id=patient.id,
            intervention_task_id=task_id,
            signal_id=signal_id,
            type=OutcomeType.BP,
            metric_name="systolic_bp",
            value_numeric=value_numeric,
            unit="mmHg",
            observed_at=_now() + timedelta(hours=1),
            source="railway_demo_seed",
        ),
    )


def _ensure_care_update(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
    escalation_id: UUID,
    task_id: UUID,
    outcome_id: UUID,
    summary: str,
):
    care_updates = list_care_updates_for_patient(db=db, context=context, patient=patient)
    care_update = next((item for item in care_updates if item.intervention_task_id == task_id), None)
    if care_update is not None:
        return care_update
    return create_care_update(
        db,
        context=context,
        payload=CareUpdateCreate(
            patient_id=patient.id,
            summary=summary,
            details="Synthetic Railway demo care update. No real PHI.",
            care_update_type=CareUpdateType.FOLLOW_UP,
            occurred_at=_now() + timedelta(hours=90),
            escalation_id=escalation_id,
            intervention_task_id=task_id,
            outcome_id=outcome_id,
        ),
    )


def _latest_matching_snapshot(
    *,
    db: Session,
    context: RequestContext,
    patient: Patient,
    predicate,
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
    return snapshots[0] if predicate(audit_status) else None


def _assert_normal_approval_blocked(
    *,
    db: Session,
    context: RequestContext,
    snapshot_id: UUID,
) -> None:
    try:
        update_access_review_packet_snapshot_review(
            db=db,
            context=context,
            snapshot_id=snapshot_id,
            review_status="approved",
            review_note="Normal approval should be blocked for this demo case.",
            decision_note="Normal approval should be blocked for this demo case.",
        )
    except AccessReviewPacketApprovalBlockedError:
        db.rollback()
        return
    raise RuntimeError(f"Snapshot {snapshot_id} allowed normal approval unexpectedly.")


def _ensure_json_export_recorded(
    *,
    db: Session,
    context: RequestContext,
    snapshot_id: UUID,
) -> None:
    events = list_access_review_packet_snapshot_events(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    if events is not None and any(
        event["event_type"] == "audit_bundle_exported"
        and (event.get("metadata") or {}).get("export_format") == "json"
        for event in events["events"]
    ):
        return

    bundle = get_access_review_packet_snapshot_audit_bundle(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    if bundle is None:
        raise RuntimeError(f"Snapshot {snapshot_id} is missing an audit bundle.")
    record_access_review_packet_snapshot_audit_bundle_export(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
        export_format="json",
        export_metadata=build_access_review_packet_snapshot_export_metadata(
            snapshot_id=snapshot_id,
            export_format="json",
        ),
    )


def _assert_manifest_verifies(
    *,
    db: Session,
    context: RequestContext,
    snapshot_id: UUID,
) -> None:
    bundle = get_access_review_packet_snapshot_audit_bundle(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
    )
    if bundle is None:
        raise RuntimeError(f"Snapshot {snapshot_id} is missing an audit bundle.")
    result = verify_access_review_packet_snapshot_audit_manifest(
        db=db,
        context=context,
        snapshot_id=snapshot_id,
        submitted_manifest=bundle["audit_manifest"],
    )
    if result is None or not result["verified"]:
        raise RuntimeError(f"Snapshot {snapshot_id} audit manifest did not verify.")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


if __name__ == "__main__":
    main()
