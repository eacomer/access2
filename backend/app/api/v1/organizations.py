from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_superuser, get_db
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.services.organizations import (
    DuplicateOrganizationSlugError,
    create_organization,
    get_organization_by_id,
    list_organizations,
)


router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
def create_organization_endpoint(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> OrganizationRead:
    try:
        organization = create_organization(db=db, payload=payload)
    except DuplicateOrganizationSlugError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An organization with this slug already exists.",
        )

    return organization


@router.get("", response_model=List[OrganizationRead])
def list_organizations_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> List[OrganizationRead]:
    organizations = list_organizations(db=db, skip=skip, limit=limit)
    return organizations


@router.get("/{organization_id}", response_model=OrganizationRead)
def get_organization_endpoint(
    organization_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> OrganizationRead:
    organization = get_organization_by_id(db=db, organization_id=organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    return organization
