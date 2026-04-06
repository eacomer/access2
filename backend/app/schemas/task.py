from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.intervention_task import (
    InterventionTaskPriority,
    InterventionTaskStatus,
)


class InterventionTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    priority: InterventionTaskPriority = InterventionTaskPriority.MEDIUM
    due_at: datetime | None = None
    assigned_user_id: UUID | None = None


class InterventionTaskAssignRequest(BaseModel):
    assigned_user_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class InterventionTaskDueDateRequest(BaseModel):
    due_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class InterventionTaskCompleteRequest(BaseModel):
    completion_note: str | None = Field(default=None, max_length=4000)

    model_config = ConfigDict(extra="forbid")


class InterventionTaskRead(BaseModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    enrollment_id: UUID | None
    escalation_id: UUID
    assigned_user_id: UUID | None
    created_by_user_id: UUID
    title: str
    description: str | None
    status: InterventionTaskStatus
    priority: InterventionTaskPriority
    due_at: datetime | None
    completed_at: datetime | None
    completed_by_user_id: UUID | None
    completion_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
