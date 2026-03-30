from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.services.users import get_user_by_email


class InvalidCredentialsError(Exception):
    """Raised when a user provides invalid credentials."""


class InactiveUserError(Exception):
    """Raised when an inactive user attempts to authenticate."""


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = get_user_by_email(db=db, email=email)
    if user is None:
        raise InvalidCredentialsError()

    if not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()

    if not user.is_active:
        raise InactiveUserError()

    return user


def issue_access_token(user: User) -> str:
    return create_access_token(subject=str(user.id))
