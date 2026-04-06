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
    CareUpdateNotFoundError,
    CareUpdateValidationError,
    create_care_update,
    get_care_update_by_id,
    list_care_updates_for_escalation,
    list_care_updates_for_patient,
    list_care_updates_for_task,
)
from app.services.intervention_task_service import (
    InterventionTaskNotFoundError,
    get_task_by_id,
)
from app.services.patient_service import PatientNotFoundError, get_patient_by_id
from app.services.patient_signal_service import (
    PatientEscalationNotFoundError,
    get_escalation_by_id,
)


router = APIRouter(tags=["care_updates"])


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
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)

    try:
        care_update = create_care_update(
            db=db,
            context=context,
            patient=patient,
            payload=payload,
        )
    except CareUpdateValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except CareUpdateLinkageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return care_update


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


@router.get(
    "/escalations/{escalation_id}/care-updates",
    response_model=List[CareUpdateRead],
)
def list_care_updates_for_escalation_endpoint(
    escalation_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[CareUpdateRead]:
    escalation = _get_escalation_or_error(db=db, context=context, escalation_id=escalation_id)
    return list_care_updates_for_escalation(db=db, context=context, escalation=escalation)


@router.get(
    "/intervention-tasks/{task_id}/care-updates",
    response_model=List[CareUpdateRead],
)
def list_care_updates_for_task_endpoint(
    task_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[CareUpdateRead]:
    task = _get_task_or_error(db=db, context=context, task_id=task_id)
    return list_care_updates_for_task(db=db, context=context, task=task)


@router.get(
    "/care-updates/{care_update_id}",
    response_model=CareUpdateRead,
)
def get_care_update_endpoint(
    care_update_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> CareUpdateRead:
    try:
        return get_care_update_by_id(
            db=db,
            context=context,
            care_update_id=care_update_id,
        )
    except CareUpdateNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Care update not found.",
        )
    except OrganizationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )


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


def _get_escalation_or_error(
    *,
    db: Session,
    context: RequestContext,
    escalation_id: UUID,
):
    try:
        return get_escalation_by_id(db=db, context=context, escalation_id=escalation_id)
    except PatientEscalationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation not found.",
        )
    except OrganizationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )


def _get_task_or_error(
    *,
    db: Session,
    context: RequestContext,
    task_id: UUID,
):
    try:
        return get_task_by_id(db=db, context=context, task_id=task_id)
    except InterventionTaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )
    except OrganizationAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
