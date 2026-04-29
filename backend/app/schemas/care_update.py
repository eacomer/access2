from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.care_update import CareUpdateType


class CareUpdateCreate(BaseModel):
    patient_id: UUID
    summary: str = Field(..., min_length=1, max_length=512)
    details: str | None = Field(default=None, max_length=4000)
    care_update_type: CareUpdateType
    occurred_at: datetime | None = None
    escalation_id: UUID | None = None
    intervention_task_id: UUID | None = None
    outcome_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class CareUpdateRead(BaseModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    escalation_id: UUID | None
    intervention_task_id: UUID | None
    outcome_id: UUID | None
    created_by_user_id: UUID
    care_update_type: CareUpdateType
    summary: str
    details: str | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
