from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.intervention_task import InterventionTask
from app.models.patient import Patient
from app.models.patient_signal import (
    EscalationStatus,
    PatientEscalation,
    PatientEscalationStatusEvent,
    PatientSignal,
)
from app.models.user import User
from app.schemas.admin_workflow import (
    WorkflowBootstrapCreateRequest,
    WorkflowBootstrapCreateResponse,
)


def create_workflow_bootstrap(
    *,
    db: Session,
    current_user: User,
    payload: WorkflowBootstrapCreateRequest,
) -> WorkflowBootstrapCreateResponse:
    now = datetime.now(timezone.utc)
    recorded_at = _coerce_datetime(payload.recorded_at, fallback=now)
    sla_due_at = _coerce_optional_datetime(payload.escalation_sla_due_at)
    if sla_due_at is None:
        sla_due_at = recorded_at + timedelta(hours=24)

    patient = Patient(
        organization_id=current_user.organization_id,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        date_of_birth=payload.date_of_birth,
        sex=_clean_optional(payload.sex, lower=True),
        external_patient_id=_clean_optional(payload.external_patient_id),
    )
    db.add(patient)
    db.flush()

    signal = PatientSignal(
        organization_id=current_user.organization_id,
        patient_id=patient.id,
        enrollment_id=None,
        signal_type=payload.signal_type,
        signal_source=_clean_optional(payload.signal_source),
        signal_value_numeric=payload.signal_value_numeric,
        signal_value_text=_clean_optional(payload.signal_value_text),
        unit=_clean_optional(payload.unit),
        recorded_at=recorded_at,
        notes=_clean_optional(payload.signal_notes),
    )
    db.add(signal)
    db.flush()

    escalation = PatientEscalation(
        organization_id=current_user.organization_id,
        patient_id=patient.id,
        enrollment_id=None,
        signal_id=signal.id,
        escalation_type=payload.escalation_type.strip(),
        status=EscalationStatus.OPEN,
        severity=payload.escalation_severity,
        triggered_at=recorded_at,
        sla_due_at=sla_due_at,
    )
    db.add(escalation)
    db.flush()

    status_event = PatientEscalationStatusEvent(
        organization_id=current_user.organization_id,
        patient_id=patient.id,
        escalation_id=escalation.id,
        status=EscalationStatus.OPEN,
        occurred_at=recorded_at,
        note=_clean_optional(payload.escalation_note),
        actor_user_id=current_user.id,
    )
    db.add(status_event)
    db.flush()

    task = None
    if payload.create_open_task:
        task_due_at = _coerce_optional_datetime(payload.task_due_at)
        if task_due_at is None:
            task_due_at = recorded_at + timedelta(hours=8)

        title = (
            payload.task_title.strip()
            if payload.task_title and payload.task_title.strip()
            else f"Follow up with {patient.first_name} {patient.last_name}"
        )

        task = InterventionTask(
            organization_id=current_user.organization_id,
            patient_id=patient.id,
            enrollment_id=None,
            escalation_id=escalation.id,
            assigned_user_id=payload.task_assigned_user_id,
            created_by_user_id=current_user.id,
            title=title,
            description=_clean_optional(payload.task_description),
            priority=payload.task_priority,
            due_at=task_due_at,
        )
        db.add(task)
        db.flush()

    db.commit()

    return WorkflowBootstrapCreateResponse(
        organization_id=current_user.organization_id,
        patient_id=patient.id,
        signal_id=signal.id,
        escalation_id=escalation.id,
        status_event_id=status_event.id,
        task_id=task.id if task else None,
        patient_full_name=f"{patient.first_name} {patient.last_name}",
        signal_type=signal.signal_type,
        escalation_type=escalation.escalation_type,
        escalation_severity=escalation.severity,
        task_created=task is not None,
    )


def _clean_optional(value: str | None, *, lower: bool = False) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned.lower() if lower else cleaned


def _coerce_datetime(value: datetime | None, *, fallback: datetime) -> datetime:
    if value is None:
        return fallback
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _coerce_optional_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
