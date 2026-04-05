from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from app.schemas.enrollment import (
    PatientEnrollmentCreate,
    PatientEnrollmentRead,
    PatientEnrollmentUpdate,
)
from app.schemas.patient import PatientCreate, PatientRead
from app.services.authz import OrganizationAccessError
from app.services.patient_service import (
    DuplicateActiveEnrollmentError,
    DuplicatePatientRecordError,
    EnrollmentNotFoundError,
    PatientNotFoundError,
    create_enrollment,
    create_patient,
    get_enrollment_by_id,
    get_patient_by_id,
    list_enrollments_for_patient,
    list_patients,
    update_enrollment,
)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient_endpoint(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientRead:
    try:
        patient = create_patient(db=db, context=context, payload=payload)
    except DuplicatePatientRecordError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient already exists for this organization.",
        )

    return patient


@router.get("", response_model=List[PatientRead])
def list_patients_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[PatientRead]:
    patients = list_patients(db=db, context=context, skip=skip, limit=limit)
    return patients


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientRead:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )
    except OrganizationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    return patient


@router.post(
    "/{patient_id}/enrollments",
    response_model=PatientEnrollmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_enrollment_endpoint(
    patient_id: UUID,
    payload: PatientEnrollmentCreate,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientEnrollmentRead:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )
    except OrganizationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    try:
        enrollment = create_enrollment(
            db=db,
            context=context,
            patient=patient,
            payload=payload,
        )
    except DuplicateActiveEnrollmentError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient already has an active enrollment for this track.",
        )

    return enrollment


@router.get(
    "/{patient_id}/enrollments",
    response_model=List[PatientEnrollmentRead],
)
def list_patient_enrollments_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[PatientEnrollmentRead]:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )
    except OrganizationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    enrollments = list_enrollments_for_patient(db=db, context=context, patient=patient)
    return enrollments


@router.patch(
    "/enrollments/{enrollment_id}",
    response_model=PatientEnrollmentRead,
)
def update_enrollment_endpoint(
    enrollment_id: UUID,
    payload: PatientEnrollmentUpdate,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientEnrollmentRead:
    try:
        enrollment = get_enrollment_by_id(
            db=db,
            context=context,
            enrollment_id=enrollment_id,
        )
    except EnrollmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found.",
        )
    except OrganizationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    updated = update_enrollment(
        db=db,
        enrollment=enrollment,
        payload=payload,
    )
    return updated
