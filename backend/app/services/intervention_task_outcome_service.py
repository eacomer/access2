from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.intervention_task import InterventionTask, InterventionTaskStatus
from app.models.intervention_task_outcome import InterventionTaskOutcome
from app.models.patient import Patient
from app.models.patient_signal import PatientEscalation
from app.schemas.task_outcome import InterventionTaskOutcomeCreate
from app.services.authz import ensure_tenant_scoped_resource
from app.services.intervention_task_service import TaskStateError


class TaskOutcomeExistsError(Exception):
    """Raised when attempting to record a duplicate task outcome."""


class TaskOutcomeNotFoundError(Exception):
    """Raised when an outcome cannot be located for the requested scope."""


class TaskOutcomeValidationError(Exception):
    """Raised when provided data is invalid for a task outcome."""


def complete_task_with_outcome(
    db: Session,
    *,
    context: RequestContext,
    task: InterventionTask,
    payload: InterventionTaskOutcomeCreate,
) -> InterventionTaskOutcome:
    ensure_tenant_scoped_resource(context=context, resource=task)

    if task.status == InterventionTaskStatus.CANCELLED:
        raise TaskStateError("Cancelled tasks cannot be completed.")
    if task.status == InterventionTaskStatus.COMPLETED:
        raise TaskStateError("Task already completed.")

    existing = _get_outcome_for_task_id(db=db, task_id=task.id)
    if existing is not None:
        raise TaskOutcomeExistsError("Task already has completion evidence.")

    completed_at = datetime.now(timezone.utc)

    summary = _clean_required(payload.completion_summary, field="completion_summary")
    intervention_type = _clean_required(payload.intervention_type, field="intervention_type")

    outcome = InterventionTaskOutcome(
        organization_id=task.organization_id,
        intervention_task_id=task.id,
        patient_id=task.patient_id,
        escalation_id=task.escalation_id,
        completed_by_user_id=context.user.id,
        completion_summary=summary,
        intervention_type=intervention_type,
        outcome_status=payload.outcome_status,
        patient_response=_clean_optional(payload.patient_response),
        follow_up_required=payload.follow_up_required,
        follow_up_notes=_clean_optional(payload.follow_up_notes),
        completed_at=completed_at,
    )

    task.status = InterventionTaskStatus.COMPLETED
    task.completed_at = completed_at
    task.completed_by_user_id = context.user.id
    if payload.completion_note is not None:
        task.completion_note = _clean_optional(payload.completion_note)

    db.add(outcome)
    db.add(task)
    db.commit()
    db.refresh(outcome)
    db.refresh(task)
    return outcome


def get_outcome_for_task(
    db: Session,
    *,
    context: RequestContext,
    task: InterventionTask,
) -> InterventionTaskOutcome:
    ensure_tenant_scoped_resource(context=context, resource=task)
    outcome = _get_outcome_for_task_id(db=db, task_id=task.id)
    if outcome is None:
        raise TaskOutcomeNotFoundError()
    return outcome


def list_task_outcomes_for_patient(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> List[InterventionTaskOutcome]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    stmt = (
        select(InterventionTaskOutcome)
        .where(InterventionTaskOutcome.patient_id == patient.id)
        .order_by(
            InterventionTaskOutcome.completed_at.desc(),
            InterventionTaskOutcome.created_at.desc(),
        )
    )
    return list(db.execute(stmt).scalars().all())


def list_task_outcomes_for_escalation(
    db: Session,
    *,
    context: RequestContext,
    escalation: PatientEscalation,
) -> List[InterventionTaskOutcome]:
    ensure_tenant_scoped_resource(context=context, resource=escalation)
    stmt = (
        select(InterventionTaskOutcome)
        .where(InterventionTaskOutcome.escalation_id == escalation.id)
        .order_by(
            InterventionTaskOutcome.completed_at.desc(),
            InterventionTaskOutcome.created_at.desc(),
        )
    )
    return list(db.execute(stmt).scalars().all())


def _get_outcome_for_task_id(
    *,
    db: Session,
    task_id: UUID,
) -> InterventionTaskOutcome | None:
    stmt = (
        select(InterventionTaskOutcome)
        .where(InterventionTaskOutcome.intervention_task_id == task_id)
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_required(value: str, *, field: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise TaskOutcomeValidationError(f"{field} cannot be blank.")
    return cleaned
