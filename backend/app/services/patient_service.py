from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import RequestContext
from app.models.patient import Patient
from app.models.patient_enrollment import (
    ConsentStatus,
    EnrollmentStatus,
    PatientEnrollment,
)
from app.schemas.enrollment import PatientEnrollmentCreate, PatientEnrollmentUpdate
from app.schemas.patient import PatientCreate
from app.services.authz import ensure_tenant_scoped_resource

ACTIVE_ENROLLMENT_STATUSES = {
    EnrollmentStatus.PENDING,
    EnrollmentStatus.ACTIVE,
}

TERMINAL_ENROLLMENT_STATUSES = {
    EnrollmentStatus.COMPLETED,
    EnrollmentStatus.DISENROLLED,
    EnrollmentStatus.INACTIVE,
}


class DuplicatePatientRecordError(Exception):
    """Raised when attempting to create an obvious duplicate patient."""


class PatientNotFoundError(Exception):
    """Raised when a patient is not found or inaccessible."""


class DuplicateActiveEnrollmentError(Exception):
    """Raised when creating a duplicate active enrollment."""


class EnrollmentNotFoundError(Exception):
    """Raised when an enrollment is not found or inaccessible."""


def create_patient(
    db: Session,
    *,
    context: RequestContext,
    payload: PatientCreate,
) -> Patient:
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    sex = payload.sex.strip().lower() if payload.sex else None
    external_id = payload.external_patient_id.strip() if payload.external_patient_id else None

    duplicate_stmt = (
        select(Patient)
        .where(
            Patient.organization_id == context.organization_id,
            func.lower(Patient.first_name) == first_name.lower(),
            func.lower(Patient.last_name) == last_name.lower(),
            Patient.date_of_birth == payload.date_of_birth,
        )
        .limit(1)
    )
    duplicate_patient = db.execute(duplicate_stmt).scalar_one_or_none()
    if duplicate_patient is not None:
        raise DuplicatePatientRecordError()

    if external_id:
        external_stmt = (
            select(Patient)
            .where(
                Patient.organization_id == context.organization_id,
                Patient.external_patient_id == external_id,
            )
            .limit(1)
        )
        external_match = db.execute(external_stmt).scalar_one_or_none()
        if external_match is not None:
            raise DuplicatePatientRecordError()

    patient = Patient(
        organization_id=context.organization_id,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=payload.date_of_birth,
        sex=sex,
        external_patient_id=external_id,
        is_active=True,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def list_patients(
    db: Session,
    *,
    context: RequestContext,
    skip: int = 0,
    limit: int = 50,
) -> List[Patient]:
    stmt = select(Patient)
    if not context.is_superuser:
        stmt = stmt.where(Patient.organization_id == context.organization_id)

    stmt = stmt.order_by(Patient.created_at.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_patient_by_id(
    db: Session,
    *,
    context: RequestContext,
    patient_id: UUID,
) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise PatientNotFoundError()

    ensure_tenant_scoped_resource(context=context, resource=patient)
    return patient


def create_enrollment(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
    payload: PatientEnrollmentCreate,
) -> PatientEnrollment:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    track_code = payload.track_code.strip().lower()
    notes = payload.notes.strip() if payload.notes else None

    existing_stmt = (
        select(PatientEnrollment)
        .where(
            PatientEnrollment.patient_id == patient.id,
            PatientEnrollment.track_code == track_code,
            PatientEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES),
        )
        .limit(1)
    )
    existing = db.execute(existing_stmt).scalar_one_or_none()
    if existing is not None:
        raise DuplicateActiveEnrollmentError()

    enrollment = PatientEnrollment(
        organization_id=patient.organization_id,
        patient_id=patient.id,
        track_code=track_code,
        enrollment_status=payload.enrollment_status,
        consent_status=payload.consent_status,
        notes=notes,
    )
    _apply_enrollment_state_rules(enrollment)

    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def list_enrollments_for_patient(
    db: Session,
    *,
    context: RequestContext,
    patient: Patient,
) -> List[PatientEnrollment]:
    ensure_tenant_scoped_resource(context=context, resource=patient)

    stmt = (
        select(PatientEnrollment)
        .where(PatientEnrollment.patient_id == patient.id)
        .order_by(PatientEnrollment.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_enrollment_by_id(
    db: Session,
    *,
    context: RequestContext,
    enrollment_id: UUID,
) -> PatientEnrollment:
    enrollment = db.get(PatientEnrollment, enrollment_id)
    if enrollment is None:
        raise EnrollmentNotFoundError()

    ensure_tenant_scoped_resource(context=context, resource=enrollment)
    return enrollment


def update_enrollment(
    db: Session,
    *,
    enrollment: PatientEnrollment,
    payload: PatientEnrollmentUpdate,
) -> PatientEnrollment:
    if payload.enrollment_status is not None:
        enrollment.enrollment_status = payload.enrollment_status

    if payload.consent_status is not None:
        enrollment.consent_status = payload.consent_status

    if payload.notes is not None:
        enrollment.notes = payload.notes.strip() or None

    _apply_enrollment_state_rules(enrollment)

    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def _apply_enrollment_state_rules(enrollment: PatientEnrollment) -> None:
    now = datetime.now(timezone.utc)

    if enrollment.consent_status == ConsentStatus.CONSENTED and enrollment.consented_at is None:
        enrollment.consented_at = now

    if (
        enrollment.enrollment_status == EnrollmentStatus.ACTIVE
        and enrollment.enrollment_started_at is None
    ):
        enrollment.enrollment_started_at = now

    if (
        enrollment.enrollment_status in TERMINAL_ENROLLMENT_STATUSES
        and enrollment.enrollment_ended_at is None
    ):
        enrollment.enrollment_ended_at = now
