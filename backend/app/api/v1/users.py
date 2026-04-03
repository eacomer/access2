from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_superuser, get_db
from app.models.user import User
from app.schemas.user import UserAdminUpdate, UserCreate, UserRead
from app.services.users import (
    DuplicateEmailError,
    InvalidOrganizationError,
    create_user,
    get_user_by_id,
    list_users,
    update_user,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user_endpoint(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> UserRead:
    try:
        user = create_user(db=db, user_in=payload)
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    except InvalidOrganizationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization not found or inactive.",
        )

    return user


@router.get(
    "",
    response_model=List[UserRead],
    status_code=status.HTTP_200_OK,
)
def list_users_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> List[UserRead]:
    users = list_users(db=db, skip=skip, limit=limit)
    return users


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def get_user_endpoint(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> UserRead:
    user = get_user_by_id(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def update_user_endpoint(
    user_id: UUID,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> UserRead:
    user = get_user_by_id(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    updated_user = update_user(db=db, user=user, user_in=payload)
    return updated_user
