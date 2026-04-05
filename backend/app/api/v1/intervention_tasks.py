from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from app.schemas.task import (
    InterventionTaskAssignRequest,
    InterventionTaskCompleteRequest,
    InterventionTaskCreate,
    InterventionTaskRead,
)
from app.services.authz import OrganizationAccessError
from app.services.intervention_task_service import (
    InterventionTaskNotFoundError,
    TaskAssignmentError,
    TaskStateError,
    assign_task,
    cancel_task,
    complete_task,
    create_task_from_escalation,
    get_task_by_id,
    list_tasks_for_escalation,
    list_tasks_for_patient,
    start_task,
)
from app.services.patient_service import PatientNotFoundError, get_patient_by_id
from app.services.patient_signal_service import (
    PatientEscalationNotFoundError,
    get_escalation_by_id,
)


router = APIRouter(tags=["intervention_tasks"])


@router.post(
    "/escalations/{escalation_id}/tasks",
    response_model=InterventionTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task_for_escalation_endpoint(
    escalation_id: UUID,
    payload: InterventionTaskCreate,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> InterventionTaskRead:
    escalation = _get_escalation_or_error(db=db, context=context, escalation_id=escalation_id)

    try:
        task = create_task_from_escalation(
            db=db,
            context=context,
            escalation=escalation,
            payload=payload,
        )
    except TaskAssignmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return task


@router.get(
    "/patients/{patient_id}/tasks",
    response_model=List[InterventionTaskRead],
)
def list_tasks_for_patient_endpoint(
    patient_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[InterventionTaskRead]:
    patient = _get_patient_or_error(db=db, context=context, patient_id=patient_id)
    tasks = list_tasks_for_patient(db=db, context=context, patient=patient)
    return tasks


@router.get(
    "/escalations/{escalation_id}/tasks",
    response_model=List[InterventionTaskRead],
)
def list_tasks_for_escalation_endpoint(
    escalation_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> List[InterventionTaskRead]:
    escalation = _get_escalation_or_error(db=db, context=context, escalation_id=escalation_id)
    tasks = list_tasks_for_escalation(db=db, context=context, escalation=escalation)
    return tasks


@router.get(
    "/tasks/{task_id}",
    response_model=InterventionTaskRead,
)
def get_task_endpoint(
    task_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> InterventionTaskRead:
    return _get_task_or_error(db=db, context=context, task_id=task_id)


@router.post(
    "/tasks/{task_id}/assign",
    response_model=InterventionTaskRead,
)
def assign_task_endpoint(
    task_id: UUID,
    payload: InterventionTaskAssignRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> InterventionTaskRead:
    task = _get_task_or_error(db=db, context=context, task_id=task_id)
    try:
        updated = assign_task(
            db=db,
            context=context,
            task=task,
            assigned_user_id=payload.assigned_user_id,
        )
    except TaskAssignmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except TaskStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return updated


@router.post(
    "/tasks/{task_id}/start",
    response_model=InterventionTaskRead,
)
def start_task_endpoint(
    task_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> InterventionTaskRead:
    task = _get_task_or_error(db=db, context=context, task_id=task_id)
    try:
        updated = start_task(db=db, context=context, task=task)
    except TaskStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return updated


@router.post(
    "/tasks/{task_id}/complete",
    response_model=InterventionTaskRead,
)
def complete_task_endpoint(
    task_id: UUID,
    payload: InterventionTaskCompleteRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> InterventionTaskRead:
    task = _get_task_or_error(db=db, context=context, task_id=task_id)

    try:
        updated = complete_task(
            db=db,
            context=context,
            task=task,
            completion_note=payload.completion_note,
        )
    except TaskStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return updated


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=InterventionTaskRead,
)
def cancel_task_endpoint(
    task_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> InterventionTaskRead:
    task = _get_task_or_error(db=db, context=context, task_id=task_id)

    try:
        updated = cancel_task(db=db, context=context, task=task)
    except TaskStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return updated


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

