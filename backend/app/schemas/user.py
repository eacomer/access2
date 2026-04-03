from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    password: str
    organization_id: UUID


class UserAdminUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class UserRead(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    organization_id: UUID

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserRead):
    hashed_password: str
