from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from app.models.patient_signal import EscalationStatus
from app.schemas.signal import (
    EscalationResolveRequest,
    EscalationSLAUpdateRequest,
    EscalationStatusUpdateRequest,
    PatientEscalationRead,
)
from app.services.authz import OrganizationAccessError
from app.services.patient_signal_service import (
    EscalationTransitionError,
    PatientEscalationNotFoundError,
    get_escalation_by_id,
    transition_escalation_status,
    update_escalation_sla_due_at,
)

router = APIRouter(prefix="/escalations", tags=["escalations"])


@router.get(
    "/{escalation_id}",
    response_model=PatientEscalationRead,
)
def get_escalation_endpoint(
    escalation_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientEscalationRead:
    return _get_escalation_or_error(db=db, context=context, escalation_id=escalation_id)


@router.post(
    "/{escalation_id}/acknowledge",
    response_model=PatientEscalationRead,
)
def acknowledge_escalation_endpoint(
    escalation_id: UUID,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientEscalationRead:
    return _update_status_response(
        db=db,
        escalation_id=escalation_id,
        context=context,
        new_status=EscalationStatus.IN_PROGRESS,
    )


@router.post(
    "/{escalation_id}/resolve",
    response_model=PatientEscalationRead,
)
def resolve_escalation_endpoint(
    escalation_id: UUID,
    payload: EscalationResolveRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientEscalationRead:
    return _update_status_response(
        db=db,
        escalation_id=escalation_id,
        context=context,
        new_status=EscalationStatus.RESOLVED,
        note=payload.resolution_notes,
    )


@router.post(
    "/{escalation_id}/status",
    response_model=PatientEscalationRead,
)
def update_escalation_status_endpoint(
    escalation_id: UUID,
    payload: EscalationStatusUpdateRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientEscalationRead:
    return _update_status_response(
        db=db,
        escalation_id=escalation_id,
        context=context,
        new_status=payload.status,
        note=payload.note,
    )


@router.post(
    "/{escalation_id}/sla",
    response_model=PatientEscalationRead,
)
def update_escalation_sla_endpoint(
    escalation_id: UUID,
    payload: EscalationSLAUpdateRequest,
    db: Session = Depends(get_db),
    context: RequestContext = Depends(get_request_context),
) -> PatientEscalationRead:
    escalation = _get_escalation_or_error(db=db, context=context, escalation_id=escalation_id)
    updated = update_escalation_sla_due_at(
        db=db,
        escalation=escalation,
        sla_due_at=payload.sla_due_at,
    )
    return updated


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


def _update_status_response(
    *,
    db: Session,
    escalation_id: UUID,
    context: RequestContext,
    new_status: EscalationStatus,
    note: str | None = None,
) -> PatientEscalationRead:
    escalation = _get_escalation_or_error(db=db, context=context, escalation_id=escalation_id)

    try:
        updated = transition_escalation_status(
            db=db,
            escalation=escalation,
            new_status=new_status,
            note=note,
            actor_user_id=context.user.id,
        )
    except EscalationTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return updated
