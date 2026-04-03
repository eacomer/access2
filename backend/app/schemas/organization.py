from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrganizationBase(BaseModel):
    name: str
    slug: str
    is_active: bool = True


class OrganizationCreate(BaseModel):
    name: str
    slug: str


class OrganizationRead(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    slug: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
