from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_context
from app.core.context import RequestContext
from app.schemas.signal import EscalationResolveRequest, PatientEscalationRead
from app.services.authz import OrganizationAccessError
from app.services.patient_signal_service import (
    EscalationTransitionError,
    PatientEscalationNotFoundError,
    acknowledge_escalation,
    get_escalation_by_id,
    resolve_escalation,
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
    escalation = _get_escalation_or_error(db=db, context=context, escalation_id=escalation_id)

    try:
        updated = acknowledge_escalation(db=db, escalation=escalation)
    except EscalationTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return updated


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
    escalation = _get_escalation_or_error(db=db, context=context, escalation_id=escalation_id)

    try:
        updated = resolve_escalation(
            db=db,
            escalation=escalation,
            resolution_notes=payload.resolution_notes,
        )
    except EscalationTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
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

