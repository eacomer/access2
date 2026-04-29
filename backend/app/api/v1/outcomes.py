from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from app.schemas.outcome import OutcomeCreate, OutcomeRead
from app.services.authz import OrganizationAccessError
from app.services.outcome_service import OutcomeValidationError, create_outcome, list_outcomes_for_patient
from app.services.patient_service import PatientNotFoundError, get_patient_by_id

router = APIRouter(tags=["outcomes"])


@router.post("/outcomes", response_model=OutcomeRead, status_code=status.HTTP_201_CREATED)
def create_outcome_endpoint(
    payload: OutcomeCreate,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> OutcomeRead:
    try:
        return create_outcome(db=db, context=context, payload=payload)
    except OutcomeValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/patients/{patient_id}/outcomes", response_model=List[OutcomeRead])
def list_patient_outcomes_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[OutcomeRead]:
    try:
        patient = get_patient_by_id(db=db, context=context, patient_id=patient_id)
    except PatientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    except OrganizationAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return list_outcomes_for_patient(db=db, context=context, patient=patient)
