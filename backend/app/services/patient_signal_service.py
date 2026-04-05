from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.patient import Patient
from app.models.patient_enrollment import PatientEnrollment
from app.models.patient_signal import (
    EscalationSeverity,
    EscalationStatus,
    PatientEscalation,
    PatientSignal,
    SignalType,
)
from app.schemas.signal import PatientSignalCreate
from app.services.authz import ensure_tenant_scoped_resource
from app.services.patient_service import (
    EnrollmentNotFoundError,
    get_enrollment_by_id,
)

SYMPTOM_SCORE_THRESHOLD = 8.0
BLOOD_PRESSURE_SYSTOLIC_THRESHOLD = 160.0


class EnrollmentMismatchError(Exception):
    """Raised when the provided enrollment does not match the patient."""


class PatientEscalationNotFoundError(Exception):
    """Raised when an escalation cannot be located."""


class EscalationTransitionError(Exception):
    """Raised when applying an invalid escalation state transition."""


@dataclass(slots=True)
class EscalationRuleResult:
    escalation_type: str
    severity: EscalationSeverity


def create_patient_signal(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    payload: PatientSignalCreate,
) -> Tuple[PatientSignal, PatientEscalation | None]:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    enrollment: PatientEnrollment | None = None
    if payload.enrollment_id:
        try:
            enrollment = get_enrollment_by_id(
                db=db,
                context=context,
                enrollment_id=payload.enrollment_id,
            )
        except EnrollmentNotFoundError as exc:
            raise EnrollmentMismatchError() from exc

        if enrollment.patient_id != patient.id:
            raise EnrollmentMismatchError()

    signal = PatientSignal(
        organization_id=patient.organization_id,
        patient_id=patient.id,
        enrollment_id=enrollment.id if enrollment else None,
        signal_type=payload.signal_type,
        signal_source=_clean_optional(payload.signal_source),
        signal_value_numeric=payload.signal_value_numeric,
        signal_value_text=_clean_optional(payload.signal_value_text),
        unit=_clean_optional(payload.unit),
        recorded_at=payload.recorded_at or datetime.now(timezone.utc),
        notes=_clean_optional(payload.notes),
    )

    db.add(signal)
    db.flush()

    escalation = _maybe_create_escalation(db=db, signal=signal)

    db.commit()
    db.refresh(signal)
    if escalation:
        db.refresh(escalation)

    return signal, escalation


def list_patient_signals(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    skip: int = 0,
    limit: int = 100,
) -> List[PatientSignal]:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    stmt = (
        select(PatientSignal)
        .where(PatientSignal.patient_id == patient.id)
        .order_by(PatientSignal.recorded_at.desc(), PatientSignal.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def list_patient_escalations(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> List[PatientEscalation]:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    stmt = (
        select(PatientEscalation)
        .where(PatientEscalation.patient_id == patient.id)
        .order_by(PatientEscalation.triggered_at.desc(), PatientEscalation.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_escalation_by_id(
    db: Session,
    *,
    context: RequestContext,
    escalation_id: UUID,
) -> PatientEscalation:
    escalation = db.get(PatientEscalation, escalation_id)
    if escalation is None:
        raise PatientEscalationNotFoundError()

    ensure_tenant_scoped_resource(context=context, resource=escalation)
    return escalation


def acknowledge_escalation(
    db: Session,
    *,
    escalation: PatientEscalation,
) -> PatientEscalation:
    if escalation.status == EscalationStatus.RESOLVED:
        raise EscalationTransitionError("Resolved escalations cannot be acknowledged.")

    if escalation.acknowledged_at is None:
        escalation.acknowledged_at = datetime.now(timezone.utc)
        escalation.status = EscalationStatus.ACKNOWLEDGED
        db.add(escalation)
        db.commit()
        db.refresh(escalation)

    return escalation


def resolve_escalation(
    db: Session,
    *,
    escalation: PatientEscalation,
    resolution_notes: str | None = None,
) -> PatientEscalation:
    if escalation.status == EscalationStatus.RESOLVED:
        raise EscalationTransitionError("Escalation already resolved.")

    escalation.status = EscalationStatus.RESOLVED
    escalation.resolved_at = datetime.now(timezone.utc)
    if resolution_notes is not None:
        escalation.resolution_notes = _clean_optional(resolution_notes)

    if escalation.acknowledged_at is None:
        escalation.acknowledged_at = datetime.now(timezone.utc)

    db.add(escalation)
    db.commit()
    db.refresh(escalation)
    return escalation


def _maybe_create_escalation(
    *,
    db: Session,
    signal: PatientSignal,
) -> PatientEscalation | None:
    rule_result = _evaluate_signal(signal)
    if rule_result is None:
        return None

    existing_stmt = (
        select(PatientEscalation)
        .where(PatientEscalation.signal_id == signal.id)
        .limit(1)
    )
    if db.execute(existing_stmt).scalar_one_or_none():
        return None

    escalation = PatientEscalation(
        organization_id=signal.organization_id,
        patient_id=signal.patient_id,
        enrollment_id=signal.enrollment_id,
        signal_id=signal.id,
        escalation_type=rule_result.escalation_type,
        status=EscalationStatus.OPEN,
        severity=rule_result.severity,
        triggered_at=signal.recorded_at,
    )

    db.add(escalation)
    return escalation


def _evaluate_signal(signal: PatientSignal) -> EscalationRuleResult | None:
    value = signal.signal_value_numeric

    if signal.signal_type == SignalType.SYMPTOM_SCORE and value is not None:
        if value >= SYMPTOM_SCORE_THRESHOLD:
            return EscalationRuleResult(
                escalation_type="symptom_score_threshold",
                severity=EscalationSeverity.HIGH,
            )

    if signal.signal_type == SignalType.BLOOD_PRESSURE_SYSTOLIC and value is not None:
        if value >= BLOOD_PRESSURE_SYSTOLIC_THRESHOLD:
            return EscalationRuleResult(
                escalation_type="blood_pressure_systolic_threshold",
                severity=EscalationSeverity.MEDIUM,
            )

    if signal.signal_type == SignalType.MISSED_CHECK_IN:
        return EscalationRuleResult(
            escalation_type="missed_check_in",
            severity=EscalationSeverity.MEDIUM,
        )

    return None


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None

