from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from app.schemas.signal import (
    PatientEscalationRead,
    PatientSignalCreate,
    PatientSignalRead,
    SignalCreateResponse,
)
from app.services.authz import OrganizationAccessError
from app.services.patient_service import PatientNotFoundError, get_patient_by_id
from app.services.patient_signal_service import (
    EnrollmentMismatchError,
    create_patient_signal,
    list_patient_escalations,
    list_patient_signals,
)

router = APIRouter(prefix="/patients", tags=["signals"])


@router.post(
    "/{patient_id}/signals",
    response_model=SignalCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_signal_endpoint(
    patient_id: UUID,
    payload: PatientSignalCreate,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> SignalCreateResponse:
    patient = _get_patient_or_404(db=db, context=context, patient_id=patient_id)

    try:
        signal, escalation = create_patient_signal(
            db=db,
            context=context,
            patient=patient,
            payload=payload,
        )
    except EnrollmentMismatchError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment must belong to the specified patient and organization.",
        )

    return SignalCreateResponse(signal=signal, escalation=escalation)


@router.get(
    "/{patient_id}/signals",
    response_model=List[PatientSignalRead],
)
def list_signals_endpoint(
    patient_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[PatientSignalRead]:
    patient = _get_patient_or_404(db=db, context=context, patient_id=patient_id)

    signals = list_patient_signals(
        db=db,
        context=context,
        patient=patient,
        skip=skip,
        limit=limit,
    )
    return signals


@router.get(
    "/{patient_id}/escalations",
    response_model=List[PatientEscalationRead],
)
def list_patient_escalations_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[PatientEscalationRead]:
    patient = _get_patient_or_404(db=db, context=context, patient_id=patient_id)
    escalations = list_patient_escalations(db=db, context=context, patient=patient)
    return escalations


def _get_patient_or_404(
    *,
    db: Session,
    context: RequestContext,
    patient_id: UUID,
):
    try:
        return get_patient_by_id(db=db, context=context, patient_id=patient_id)
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

