from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.outcome import OutcomeType


class OutcomeCreate(BaseModel):
    patient_id: UUID
    intervention_task_id: UUID | None = None
    signal_id: UUID | None = None
    type: OutcomeType
    metric_name: str = Field(..., min_length=1, max_length=128)
    value_numeric: float | None = None
    value_text: str | None = Field(default=None, max_length=4000)
    unit: str | None = Field(default=None, max_length=32)
    observed_at: datetime
    source: str | None = Field(default=None, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_value_present(self) -> "OutcomeCreate":
        if self.value_numeric is None and _clean_optional(self.value_text) is None:
            raise ValueError("At least one of value_numeric or value_text is required.")
        return self


class OutcomeRead(BaseModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    intervention_task_id: UUID | None
    signal_id: UUID | None
    type: OutcomeType
    metric_name: str
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    observed_at: datetime
    source: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
