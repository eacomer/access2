from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.schemas.user import UserAdminUpdate, UserCreate


class DuplicateEmailError(Exception):
    """Raised when attempting to create a user with an email that already exists."""


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    stmt = select(User).where(User.id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    stmt = select(User).where(User.email == normalized_email)
    return db.execute(stmt).scalar_one_or_none()


def list_users(db: Session, skip: int = 0, limit: int = 50) -> List[User]:
    stmt = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    return list(db.execute(stmt).scalars().all())


class InvalidOrganizationError(Exception):
    """Raised when a user references an organization that does not exist."""


def create_user(db: Session, user_in: UserCreate) -> User:
    normalized_email = user_in.email.strip().lower()

    existing_user = get_user_by_email(db=db, email=normalized_email)
    if existing_user is not None:
        raise DuplicateEmailError()

    organization = db.get(Organization, user_in.organization_id)
    if organization is None or not organization.is_active:
        raise InvalidOrganizationError()

    user = User(
        email=normalized_email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False,
        organization_id=organization.id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, user_in: UserAdminUpdate) -> User:
    if user_in.full_name is not None:
        user.full_name = user_in.full_name

    if user_in.is_active is not None:
        user.is_active = user_in.is_active

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
