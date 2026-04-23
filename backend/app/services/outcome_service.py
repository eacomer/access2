from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.intervention_task import InterventionTask
from app.models.outcome import Outcome
from app.models.patient import Patient
from app.models.patient_signal import PatientSignal
from app.schemas.outcome import OutcomeCreate
from app.services.authz import ensure_tenant_scoped_resource


class OutcomeValidationError(Exception):
    """Raised when an outcome payload references inconsistent patient data."""


def create_outcome(
    db: Session,
    *,
    context: RequestContext,
    payload: OutcomeCreate,
) -> Outcome:
    patient = db.get(Patient, payload.patient_id)
    if patient is None:
        raise OutcomeValidationError("Patient not found.")
    ensure_tenant_scoped_resource(context=context, resource=patient)

    task: InterventionTask | None = None
    if payload.intervention_task_id is not None:
        task = db.get(InterventionTask, payload.intervention_task_id)
        if task is None or task.patient_id != patient.id:
            raise OutcomeValidationError("Intervention task not found for this patient.")
        ensure_tenant_scoped_resource(context=context, resource=task)

    signal: PatientSignal | None = None
    if payload.signal_id is not None:
        signal = db.get(PatientSignal, payload.signal_id)
        if signal is None or signal.patient_id != patient.id:
            raise OutcomeValidationError("Signal not found for this patient.")
        ensure_tenant_scoped_resource(context=context, resource=signal)

    outcome = Outcome(
        organization_id=patient.organization_id,
        patient_id=patient.id,
        intervention_task_id=task.id if task else None,
        signal_id=signal.id if signal else None,
        type=payload.type,
        metric_name=payload.metric_name.strip(),
        value_numeric=payload.value_numeric,
        value_text=_clean_optional(payload.value_text),
        unit=_clean_optional(payload.unit),
        observed_at=payload.observed_at,
        source=_clean_optional(payload.source),
    )
    if outcome.value_numeric is None and outcome.value_text is None:
        raise OutcomeValidationError("At least one of value_numeric or value_text is required.")

    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


def list_outcomes_for_patient(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> List[Outcome]:
    ensure_tenant_scoped_resource(context=context, resource=patient)
    stmt = (
        select(Outcome)
        .where(Outcome.patient_id == patient.id)
        .order_by(Outcome.observed_at, Outcome.id)
    )
    return list(db.execute(stmt).scalars().all())


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
