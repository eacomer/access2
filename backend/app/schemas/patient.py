from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    sex: str | None = Field(default=None, max_length=32)
    external_patient_id: str | None = Field(default=None, max_length=64)


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=255)
    last_name: str | None = Field(default=None, min_length=1, max_length=255)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=32)
    external_patient_id: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class PatientRead(PatientBase):
    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
