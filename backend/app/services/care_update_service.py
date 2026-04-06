from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.care_update import CareUpdate
from app.models.intervention_task import InterventionTask
from app.models.intervention_task_outcome import InterventionTaskOutcome
from app.models.patient import Patient
from app.models.patient_signal import PatientEscalation
from app.schemas.care_update import CareUpdateCreate
from app.services.authz import ensure_tenant_scoped_resource


class CareUpdateNotFoundError(Exception):
    """Raised when a care update cannot be located within scope."""


class CareUpdateLinkageError(Exception):
    """Raised when related workflow references do not align."""


class CareUpdateValidationError(Exception):
    """Raised when payload data fails validation rules."""


def create_care_update(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    payload: CareUpdateCreate,
) -> CareUpdate:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    summary = (payload.summary or "").strip()
    if not summary:
        raise CareUpdateValidationError("summary is required.")

    details = _clean_optional(payload.details)
    occurred_at = payload.occurred_at or datetime.now(timezone.utc)

    escalation = (
        _load_escalation(db=db, context=context, escalation_id=payload.escalation_id)
        if payload.escalation_id
        else None
    )
    task = (
        _load_task(db=db, context=context, task_id=payload.intervention_task_id)
        if payload.intervention_task_id
        else None
    )
    outcome = (
        _load_outcome(db=db, context=context, outcome_id=payload.intervention_task_outcome_id)
        if payload.intervention_task_outcome_id
        else None
    )

    if escalation is not None:
        _ensure_patient_match(
            patient_id=patient.id,
            resource_patient_id=escalation.patient_id,
            label="Escalation",
        )

    if task is not None:
        _ensure_patient_match(
            patient_id=patient.id,
            resource_patient_id=task.patient_id,
            label="Intervention task",
        )

    if outcome is not None:
        _ensure_patient_match(
            patient_id=patient.id,
            resource_patient_id=outcome.patient_id,
            label="Task outcome",
        )

    if task is not None and escalation is not None and task.escalation_id != escalation.id:
        raise CareUpdateLinkageError("Intervention task must belong to the provided escalation.")

    if outcome is not None and task is not None and outcome.intervention_task_id != task.id:
        raise CareUpdateLinkageError("Task outcome must belong to the provided intervention task.")

    resolved_task_id = (
        task.id if task is not None else (outcome.intervention_task_id if outcome is not None else None)
    )

    resolved_escalation_id = (
        escalation.id
        if escalation is not None
        else (
            task.escalation_id
            if task is not None and task.escalation_id is not None
            else (
                outcome.escalation_id if outcome is not None and outcome.escalation_id is not None else None
            )
        )
    )

    care_update = CareUpdate(
        organization_id=patient.organization_id,
        patient_id=patient.id,
        escalation_id=resolved_escalation_id,
        intervention_task_id=resolved_task_id,
        intervention_task_outcome_id=outcome.id if outcome is not None else None,
        created_by_user_id=context.user.id,
        care_update_type=payload.care_update_type,
        summary=summary,
        details=details,
        occurred_at=occurred_at,
    )

    db.add(care_update)
    db.commit()
    db.refresh(care_update)
    return care_update


def list_care_updates_for_patient(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> List[CareUpdate]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    stmt = (
        select(CareUpdate)
        .where(CareUpdate.patient_id == patient.id)
        .order_by(CareUpdate.occurred_at.desc(), CareUpdate.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def list_care_updates_for_escalation(
    db: Session,
    *,
    context: RequestContext,
    escalation: PatientEscalation,
) -> List[CareUpdate]:
    ensure_tenant_scoped_resource(context=context, resource=escalation)
    stmt = (
        select(CareUpdate)
        .where(CareUpdate.escalation_id == escalation.id)
        .order_by(CareUpdate.occurred_at.desc(), CareUpdate.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def list_care_updates_for_task(
    db: Session,
    *,
    context: RequestContext,
    task: InterventionTask,
) -> List[CareUpdate]:
    ensure_tenant_scoped_resource(context=context, resource=task)
    stmt = (
        select(CareUpdate)
        .where(CareUpdate.intervention_task_id == task.id)
        .order_by(CareUpdate.occurred_at.desc(), CareUpdate.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_care_update_by_id(
    db: Session,
    *,
    context: RequestContext,
    care_update_id: UUID,
) -> CareUpdate:
    care_update = db.get(CareUpdate, care_update_id)
    if care_update is None:
        raise CareUpdateNotFoundError()

    ensure_tenant_scoped_resource(context=context, resource=care_update)
    return care_update


def _load_escalation(
    *,
    db: Session,
    context: RequestContext,
    escalation_id: UUID,
) -> PatientEscalation:
    escalation = db.get(PatientEscalation, escalation_id)
    if escalation is None:
        raise CareUpdateLinkageError("Escalation reference not found.")

    ensure_tenant_scoped_resource(context=context, resource=escalation)
    return escalation


def _load_task(
    *,
    db: Session,
    context: RequestContext,
    task_id: UUID,
) -> InterventionTask:
    task = db.get(InterventionTask, task_id)
    if task is None:
        raise CareUpdateLinkageError("Intervention task reference not found.")

    ensure_tenant_scoped_resource(context=context, resource=task)
    return task


def _load_outcome(
    *,
    db: Session,
    context: RequestContext,
    outcome_id: UUID,
) -> InterventionTaskOutcome:
    outcome = db.get(InterventionTaskOutcome, outcome_id)
    if outcome is None:
        raise CareUpdateLinkageError("Task outcome reference not found.")

    ensure_tenant_scoped_resource(context=context, resource=outcome)
    return outcome


def _ensure_patient_match(
    *,
    patient_id,
    resource_patient_id,
    label: str,
) -> None:
    if resource_patient_id != patient_id:
        raise CareUpdateLinkageError(f"{label} must belong to the same patient.")


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
