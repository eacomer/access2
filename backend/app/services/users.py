from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.security import get_password_hash


def get_user_by_id(db: Session, user_id):
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.scalar(statement)


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    statement = select(User).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_user(db: Session, user_in: UserCreate) -> User:
    user = User(
        email=user_in.email,
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