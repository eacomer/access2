from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.patient_enrollment import ConsentStatus, EnrollmentStatus


class PatientEnrollmentCreate(BaseModel):
    track_code: str = Field(..., min_length=1, max_length=64)
    enrollment_status: EnrollmentStatus = EnrollmentStatus.PENDING
    consent_status: ConsentStatus = ConsentStatus.UNKNOWN
    notes: str | None = Field(default=None, max_length=2000)


class PatientEnrollmentUpdate(BaseModel):
    enrollment_status: EnrollmentStatus | None = None
    consent_status: ConsentStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class PatientEnrollmentRead(BaseModel):
    id: UUID
    patient_id: UUID
    organization_id: UUID
    track_code: str
    enrollment_status: EnrollmentStatus
    consent_status: ConsentStatus
    consented_at: datetime | None
    enrollment_started_at: datetime | None
    enrollment_ended_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
