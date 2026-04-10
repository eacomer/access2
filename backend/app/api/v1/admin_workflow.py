from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_superuser, get_db
from app.models.user import User
from app.schemas.admin_workflow import (
    WorkflowBootstrapCreateRequest,
    WorkflowBootstrapCreateResponse,
)
from app.services.workflow_bootstrap_service import create_workflow_bootstrap

router = APIRouter(prefix="/admin/workflow", tags=["admin-workflow"])


@router.post(
    "/bootstrap",
    response_model=WorkflowBootstrapCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bootstrap_endpoint(
    payload: WorkflowBootstrapCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> WorkflowBootstrapCreateResponse:
    return create_workflow_bootstrap(
        db=db,
        current_user=current_user,
        payload=payload,
    )
