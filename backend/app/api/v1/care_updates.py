from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from app.schemas.care_update import CareUpdateCreate, CareUpdateRead
from app.services.authz import OrganizationAccessError
from app.services.care_update_service import (
    CareUpdateLinkageError,
    CareUpdateValidationError,
    create_care_update,
    list_care_updates_for_patient,
)
from app.services.patient_service import PatientNotFoundError, get_patient_by_id


router = APIRouter(tags=["care_updates"])


@router.post(
    "/care-updates",
    response_model=CareUpdateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_care_update_endpoint(
    payload: CareUpdateCreate,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> CareUpdateRead:
    try:
        care_update = create_care_update(db=db, context=context, payload=payload)
    except CareUpdateValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except CareUpdateLinkageError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except OrganizationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    return care_update


@router.post(
    "/patients/{patient_id}/care-updates",
    response_model=CareUpdateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_care_update_for_patient_endpoint(
    patient_id: UUID,
    payload: CareUpdateCreate,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> CareUpdateRead:
    return create_care_update_endpoint(
        payload=payload.model_copy(update={"patient_id": patient_id}),
        db=db,
        context=context,
    )


@router.get(
    "/patients/{patient_id}/care-updates",
    response_model=List[CareUpdateRead],
)
def list_care_updates_for_patient_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[CareUpdateRead]:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    return list_care_updates_for_patient(db=db, context=context, patient=patient)


def _get_patient_or_error(
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
