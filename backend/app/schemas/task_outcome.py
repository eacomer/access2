from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.intervention_task_outcome import InterventionTaskOutcomeStatus


class InterventionTaskOutcomeCreate(BaseModel):
    completion_summary: str = Field(..., min_length=1, max_length=4000)
    intervention_type: str = Field(..., min_length=1, max_length=128)
    outcome_status: InterventionTaskOutcomeStatus
    patient_response: str | None = Field(default=None, max_length=4000)
    follow_up_required: bool = False
    follow_up_notes: str | None = Field(default=None, max_length=4000)
    completion_note: str | None = Field(default=None, max_length=4000)

    model_config = ConfigDict(extra="forbid")


class InterventionTaskOutcomeRead(BaseModel):
    id: UUID
    organization_id: UUID
    intervention_task_id: UUID
    patient_id: UUID
    escalation_id: UUID | None
    completed_by_user_id: UUID
    completion_summary: str
    intervention_type: str
    outcome_status: InterventionTaskOutcomeStatus
    patient_response: str | None
    follow_up_required: bool
    follow_up_notes: str | None
    completed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
