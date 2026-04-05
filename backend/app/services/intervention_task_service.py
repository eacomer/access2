from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.intervention_task import (
    InterventionTask,
    InterventionTaskPriority,
    InterventionTaskStatus,
)
from app.models.patient import Patient
from app.models.patient_signal import PatientEscalation
from app.schemas.task import InterventionTaskCreate
from app.services.authz import ensure_tenant_scoped_resource
from app.services.users import get_user_by_id


class InterventionTaskNotFoundError(Exception):
    """Raised when a task cannot be located within scope."""


class TaskAssignmentError(Exception):
    """Raised when assigning a user outside of the task organization."""


class TaskStateError(Exception):
    """Raised when a task transition is invalid for the current state."""


def create_task_from_escalation(
    db: Session,
    *,
    context: RequestContext,
    escalation: PatientEscalation,
    payload: InterventionTaskCreate,
) -> InterventionTask:
    ensure_tenant_scoped_resource(context=context, resource=escalation)

    task = InterventionTask(
        organization_id=escalation.organization_id,
        patient_id=escalation.patient_id,
        enrollment_id=escalation.enrollment_id,
        escalation_id=escalation.id,
        title=payload.title.strip(),
        description=_clean_optional(payload.description),
        priority=payload.priority or InterventionTaskPriority.MEDIUM,
        due_at=payload.due_at,
        status=InterventionTaskStatus.OPEN,
        created_by_user_id=context.user.id,
    )

    if payload.assigned_user_id is not None:
        task.assigned_user_id = _validate_assignee(
            db=db,
            organization_id=task.organization_id,
            user_id=payload.assigned_user_id,
        )

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks_for_patient(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> List[InterventionTask]:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    stmt = (
        select(InterventionTask)
        .where(InterventionTask.patient_id == patient.id)
        .order_by(InterventionTask.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def list_tasks_for_escalation(
    db: Session,
    *,
    context: RequestContext,
    escalation: PatientEscalation,
) -> List[InterventionTask]:
    ensure_tenant_scoped_resource(context=context, resource=escalation)

    stmt = (
        select(InterventionTask)
        .where(InterventionTask.escalation_id == escalation.id)
        .order_by(InterventionTask.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_task_by_id(
    db: Session,
    *,
    context: RequestContext,
    task_id: UUID,
) -> InterventionTask:
    task = db.get(InterventionTask, task_id)
    if task is None:
        raise InterventionTaskNotFoundError()

    ensure_tenant_scoped_resource(context=context, resource=task)
    return task


def assign_task(
    db: Session,
    *,
    context: RequestContext,
    task: InterventionTask,
    assigned_user_id: UUID | None,
) -> InterventionTask:
    ensure_tenant_scoped_resource(context=context, resource=task)
    _ensure_task_not_terminal(task)

    if assigned_user_id is None:
        task.assigned_user_id = None
    else:
        task.assigned_user_id = _validate_assignee(
            db=db,
            organization_id=task.organization_id,
            user_id=assigned_user_id,
        )

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def start_task(
    db: Session,
    *,
    context: RequestContext,
    task: InterventionTask,
) -> InterventionTask:
    ensure_tenant_scoped_resource(context=context, resource=task)
    if task.status not in {InterventionTaskStatus.OPEN}:
        raise TaskStateError("Only open tasks can be started.")

    task.status = InterventionTaskStatus.IN_PROGRESS
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def complete_task(
    db: Session,
    *,
    context: RequestContext,
    task: InterventionTask,
    completion_note: str | None = None,
) -> InterventionTask:
    ensure_tenant_scoped_resource(context=context, resource=task)
    if task.status == InterventionTaskStatus.CANCELLED:
        raise TaskStateError("Cancelled tasks cannot be completed.")
    if task.status == InterventionTaskStatus.COMPLETED:
        raise TaskStateError("Task already completed.")

    task.status = InterventionTaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by_user_id = context.user.id
    task.completion_note = _clean_optional(completion_note)

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def cancel_task(
    db: Session,
    *,
    context: RequestContext,
    task: InterventionTask,
) -> InterventionTask:
    ensure_tenant_scoped_resource(context=context, resource=task)
    if task.status == InterventionTaskStatus.COMPLETED:
        raise TaskStateError("Completed tasks cannot be cancelled.")
    if task.status == InterventionTaskStatus.CANCELLED:
        raise TaskStateError("Task already cancelled.")

    task.status = InterventionTaskStatus.CANCELLED
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _validate_assignee(
    *,
    db: Session,
    organization_id: UUID,
    user_id: UUID,
) -> UUID:
    user = get_user_by_id(db=db, user_id=user_id)
    if user is None or user.organization_id != organization_id:
        raise TaskAssignmentError("Assigned user must belong to the same organization.")
    if not user.is_active:
        raise TaskAssignmentError("Assigned user must be active.")
    return user.id


def _ensure_task_not_terminal(task: InterventionTask) -> None:
    if task.status in {InterventionTaskStatus.COMPLETED, InterventionTaskStatus.CANCELLED}:
        raise TaskStateError("Cannot modify assignments for completed or cancelled tasks.")


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
