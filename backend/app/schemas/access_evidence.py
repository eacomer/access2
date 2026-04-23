from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OutcomeMetricSummary(BaseModel):
    metric_name: str
    baseline: float | str | None = None
    latest: float | str | None = None
    delta: float | None = None
    status: str
    direction: str
    baseline_outcome_id: UUID | None = None
    latest_outcome_id: UUID | None = None


class InterventionOutcomeLink(BaseModel):
    intervention_task_id: UUID
    intervention_timestamp: datetime | None = None
    linked_outcome_ids: list[UUID] = Field(default_factory=list)
    linked_outcome_metric_names: list[str] = Field(default_factory=list)
    outcomes_after_intervention: bool
    first_outcome_lag_hours: float | None = None
    first_outcome_lag_days: float | None = None


class AccessEvidenceResponse(BaseModel):
    patient_id: UUID
    outcome_summaries: list[OutcomeMetricSummary] = Field(default_factory=list)
    intervention_outcome_links: list[InterventionOutcomeLink] = Field(default_factory=list)
