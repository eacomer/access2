from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate


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


def create_user(db: Session, user_in: UserCreate) -> User:
    normalized_email = user_in.email.strip().lower()

    existing_user = get_user_by_email(db=db, email=normalized_email)
    if existing_user is not None:
        raise DuplicateEmailError()

    user = User(
        email=normalized_email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    if user_in.full_name is not None:
        user.full_name = user_in.full_name

    if user_in.is_active is not None:
        user.is_active = user_in.is_active

    if user_in.is_superuser is not None:
        user.is_superuser = user_in.is_superuser

    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user