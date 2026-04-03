from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate


class DuplicateOrganizationSlugError(Exception):
    """Raised when attempting to create an organization with a duplicate slug."""


def list_organizations(db: Session, *, skip: int = 0, limit: int = 50) -> List[Organization]:
    stmt = (
        select(Organization)
        .offset(skip)
        .limit(limit)
        .order_by(Organization.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_organization_by_id(db: Session, organization_id: UUID) -> Organization | None:
    return db.get(Organization, organization_id)


def get_organization_by_slug(db: Session, slug: str) -> Organization | None:
    normalized_slug = slug.strip().lower()
    stmt = select(Organization).where(Organization.slug == normalized_slug)
    return db.execute(stmt).scalar_one_or_none()


def create_organization(db: Session, payload: OrganizationCreate) -> Organization:
    normalized_slug = payload.slug.strip().lower()

    existing = get_organization_by_slug(db=db, slug=normalized_slug)
    if existing is not None:
        raise DuplicateOrganizationSlugError()

    organization = Organization(
        name=payload.name.strip(),
        slug=normalized_slug,
        is_active=True,
    )
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization
