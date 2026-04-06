from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.patient_signal import (
    EscalationSeverity,
    EscalationStatus,
    SignalType,
)


class PatientSignalCreate(BaseModel):
    signal_type: SignalType
    enrollment_id: UUID | None = None
    signal_source: str | None = Field(default=None, max_length=64)
    signal_value_numeric: float | None = None
    signal_value_text: str | None = Field(default=None, max_length=2000)
    unit: str | None = Field(default=None, max_length=32)
    recorded_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class PatientSignalRead(BaseModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    enrollment_id: UUID | None
    signal_type: SignalType
    signal_source: str | None
    signal_value_numeric: float | None
    signal_value_text: str | None
    unit: str | None
    recorded_at: datetime
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientEscalationRead(BaseModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    enrollment_id: UUID | None
    signal_id: UUID | None
    escalation_type: str
    status: EscalationStatus
    severity: EscalationSeverity
    triggered_at: datetime
    in_progress_at: datetime | None
    resolved_at: datetime | None
    resolution_notes: str | None
    canceled_at: datetime | None
    cancellation_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignalCreateResponse(BaseModel):
    signal: PatientSignalRead
    escalation: PatientEscalationRead | None


class EscalationResolveRequest(BaseModel):
    resolution_notes: str | None = Field(default=None, max_length=2000)


class EscalationStatusUpdateRequest(BaseModel):
    status: EscalationStatus
    note: str | None = Field(default=None, max_length=2000)
