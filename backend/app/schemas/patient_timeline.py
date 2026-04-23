from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.intervention_task import InterventionTaskStatus


ALLOWED_TIMELINE_SOURCE_KINDS = {
    "signal",
    "escalation",
    "intervention_task",
    "intervention_task_outcome",
    "care_update",
    "escalation_status_event",
    "intervention_task_due_upcoming",
    "intervention_task_overdue",
}

ALLOWED_TIMELINE_EVENT_TYPES = {
    "signal_recorded",
    "escalation_triggered",
    "escalation_status_changed",
    "intervention_task_created",
    "intervention_task_outcome_logged",
    "care_update_logged",
    "intervention_task_due_upcoming",
    "intervention_task_due_overdue",
}

ALLOWED_TASK_STATUS_VALUES = {status.value for status in InterventionTaskStatus}


class PatientTimelineItem(BaseModel):
    event_id: str = Field(..., examples=["signal:7b6a2fbe-..."])
    event_type: str
    occurred_at: datetime
    patient_id: UUID
    organization_id: UUID
    source_id: UUID
    source_kind: str
    display_title: str
    display_text: str | None = None
    status: str | None = None
    priority: str | None = None
    authored_by_user_id: UUID | None = None
    actor_user_id: UUID | None = None
    related_escalation_id: UUID | None = None
    related_task_id: UUID | None = None
    related_outcome_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class PatientTimelineListResponse(BaseModel):
    items: list[PatientTimelineItem]
    total: int
    limit: int
    next_cursor_occurred_at: datetime | None = None
    next_cursor_event_id: str | None = None
    has_more: bool


class PatientTimelineSinceResponse(BaseModel):
    items: list[PatientTimelineItem]
    limit: int
    returned_count: int
    has_more: bool
    newest_occurred_at: datetime | None = None


class PatientEscalationEvidence(BaseModel):
    has_open_escalation: bool
    open_escalation_count: int = Field(default=0, ge=0)
    overdue_escalation_count: int = Field(default=0, ge=0)
    at_risk_escalation_count: int = Field(default=0, ge=0)
    highest_open_escalation_priority: str | None = None
    next_open_escalation_sla_due_at: datetime | None = None
    latest_open_escalation_id: UUID | None = None
    latest_open_escalation_status: str | None = None
    latest_open_escalation_created_at: datetime | None = None
    latest_escalation_event_id: str | None = None
    latest_escalation_event_type: str | None = None
    latest_escalation_event_occurred_at: datetime | None = None


class PatientTimelineDetailResponse(BaseModel):
    item: PatientTimelineItem
    escalation_evidence: PatientEscalationEvidence | None = None
    task_summary: "PatientInterventionTaskSummary | None" = None
    workflow_status: "PatientWorkflowStatusSummary | None" = None
    intervention_evidence_summary: "PatientInterventionEvidenceSummary | None" = None
    attention_summary: "PatientAttentionSummary | None" = None
    status_snapshot: str | None = None
    care_gap_label: str | None = None
    blocking_issue_label: str | None = None
    resolution_target_label: str | None = None
    closure_readiness_label: str | None = None
    closure_readiness_reason_label: str | None = None
    resolution_confidence_label: str | None = None
    resolution_confidence_reason_label: str | None = None
    active_owner_label: str | None = None
    waiting_on_label: str | None = None
    next_step_reason_detail_label: str | None = None
    status_snapshot_reason_label: str | None = None
    last_operational_change_label: str | None = None
    last_operational_change_reason_label: str | None = None
    recommended_timeframe_reason_label: str | None = None


class PatientInterventionTaskSummary(BaseModel):
    open_task_count: int = Field(default=0, ge=0)
    in_progress_task_count: int = Field(default=0, ge=0)
    overdue_task_count: int = Field(default=0, ge=0)
    latest_active_task_id: UUID | None = None
    latest_active_task_title: str | None = None
    latest_active_task_status: str | None = None
    latest_active_task_priority: str | None = None
    latest_active_task_due_at: datetime | None = None
    latest_active_task_created_at: datetime | None = None


class PatientWorkflowStatusSummary(BaseModel):
    status_key: str
    label: str
    has_active_work: bool
    primary_driver: str
    severity: str | None = None
    detail: str | None = None


class PatientInterventionEvidenceSummaryItem(BaseModel):
    title: str
    status: str | None = None
    occurred_at: datetime | None = None
    detail: str | None = None


class PatientInterventionEvidenceSummary(BaseModel):
    total_escalations: int = Field(default=0, ge=0)
    open_escalations: int = Field(default=0, ge=0)
    total_tasks: int = Field(default=0, ge=0)
    open_tasks: int = Field(default=0, ge=0)
    in_progress_tasks: int = Field(default=0, ge=0)
    completed_tasks: int = Field(default=0, ge=0)
    canceled_tasks: int = Field(default=0, ge=0)
    recent_trigger_reasons: list[PatientInterventionEvidenceSummaryItem] = Field(default_factory=list)
    recent_completed_interventions: list[PatientInterventionEvidenceSummaryItem] = Field(default_factory=list)
    current_open_work: list[PatientInterventionEvidenceSummaryItem] = Field(default_factory=list)
    evidence_event_count: int = Field(default=0, ge=0)


class PatientAttentionSummary(BaseModel):
    why_now: str
    primary_driver: str | None = None
    recommended_next_action: str
    supporting_evidence: list[str] = Field(default_factory=list)
    urgency_level: str | None = None


class PatientTimelineFilterParams(BaseModel):
    event_types: list[str] | None = Field(
        default=None,
        description="Filter timeline events to specific event types.",
    )
    occurred_after: datetime | None = Field(
        default=None,
        description="Return events that occurred on or after this timestamp.",
    )
    occurred_before: datetime | None = Field(
        default=None,
        description="Return events that occurred on or before this timestamp.",
    )
    related_escalation_id: UUID | None = None
    related_task_id: UUID | None = None
    task_statuses: list[str] | None = Field(
        default=None,
        description="Filter task-related events by intervention task statuses.",
    )
    include_only_open_work: bool = Field(
        default=False,
        description="Only include events tied to unresolved escalations or open tasks.",
    )

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        invalid = set(value) - ALLOWED_TIMELINE_EVENT_TYPES
        if invalid:
            raise ValueError(f"Unsupported event types: {', '.join(sorted(invalid))}")
        return value

    @field_validator("task_statuses")
    @classmethod
    def validate_task_statuses(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        invalid = set(value) - ALLOWED_TASK_STATUS_VALUES
        if invalid:
            raise ValueError(f"Unsupported task statuses: {', '.join(sorted(invalid))}")
        return value

    @model_validator(mode="after")
    def validate_date_range(self) -> "PatientTimelineFilterParams":
        if self.occurred_after and self.occurred_before:
            if self.occurred_after > self.occurred_before:
                raise ValueError("\"occurred_after\" must be before \"occurred_before\".")
        return self

    def to_service_filters(self):
        from app.services.patient_timeline_service import PatientTimelineFilters as ServiceFilters

        return ServiceFilters(
            event_types=tuple(self.event_types) if self.event_types else None,
            occurred_after=self.occurred_after,
            occurred_before=self.occurred_before,
            related_escalation_id=self.related_escalation_id,
            related_task_id=self.related_task_id,
            task_statuses=tuple(self.task_statuses) if self.task_statuses else None,
            include_only_open_work=self.include_only_open_work,
        )


class PatientTimelineSummaryResponse(BaseModel):
    total: int
    counts: dict[str, int]


class PatientTimelineReadStateResponse(BaseModel):
    patient_id: UUID
    user_id: UUID
    last_read_event_id: str | None = None
    last_read_occurred_at: datetime | None = None
    unread_count: int = Field(ge=0, default=0)
    newest_event_id: str | None = None
    newest_event_occurred_at: datetime | None = None


class PatientTimelineReadStateUpdateRequest(BaseModel):
    last_read_event_id: str


class PatientTimelineTargetedMarkReadRequest(BaseModel):
    event_id: str


class PatientTimelineWorkflowSummaryResponse(BaseModel):
    patient_id: UUID
    has_open_escalation: bool
    open_escalation_id: UUID | None = None
    open_escalation_severity: str | None = None
    open_escalation_triggered_at: datetime | None = None
    open_task_count: int = Field(default=0, ge=0)
    newest_open_task_id: UUID | None = None
    newest_open_task_title: str | None = None
    newest_open_task_status: str | None = None
    newest_open_task_priority: str | None = None
    newest_open_task_created_at: datetime | None = None
    latest_workflow_event_id: str | None = None
    latest_workflow_event_type: str | None = None
    latest_workflow_event_occurred_at: datetime | None = None
    unread_count: int = Field(default=0, ge=0)
    last_read_event_id: str | None = None
    last_read_occurred_at: datetime | None = None


class PatientTimelineFilterSnapshotResponse(BaseModel):
    patient_id: UUID
    total: int = Field(default=0, ge=0)
    unread_count: int = Field(default=0, ge=0)
    newest_event_id: str | None = None
    newest_event_occurred_at: datetime | None = None
    oldest_event_id: str | None = None
    oldest_event_occurred_at: datetime | None = None
    latest_workflow_event_id: str | None = None
    latest_workflow_event_type: str | None = None
    latest_workflow_event_occurred_at: datetime | None = None


class PatientTimelineInboxSummaryResponse(BaseModel):
    patient_id: UUID
    has_unread_events: bool
    unread_count: int = Field(default=0, ge=0)
    total_events: int = Field(default=0, ge=0)
    latest_event_id: str | None = None
    latest_event_type: str | None = None
    latest_event_occurred_at: datetime | None = None
    latest_event_title: str | None = None
    latest_unread_event_id: str | None = None
    latest_unread_event_type: str | None = None
    latest_unread_event_occurred_at: datetime | None = None
    oldest_unread_event_id: str | None = None
    oldest_unread_event_occurred_at: datetime | None = None


class PatientTimelineWorklistSummaryItem(BaseModel):
    patient_id: UUID
    patient_display_name: str
    has_unread_events: bool
    unread_count: int = Field(default=0, ge=0)
    total_events: int = Field(default=0, ge=0)
    latest_event_id: str | None = None
    latest_event_type: str | None = None
    latest_event_occurred_at: datetime | None = None
    latest_event_title: str | None = None
    latest_unread_event_id: str | None = None
    latest_unread_event_type: str | None = None
    latest_unread_event_occurred_at: datetime | None = None
    oldest_unread_event_id: str | None = None
    oldest_unread_event_occurred_at: datetime | None = None
    open_escalation_count: int = Field(default=0, ge=0)
    overdue_escalation_count: int = Field(default=0, ge=0)
    at_risk_escalation_count: int = Field(default=0, ge=0)
    highest_escalation_priority: str | None = None
    next_escalation_sla_due_at: datetime | None = None
    latest_open_escalation_id: UUID | None = None
    task_summary: PatientInterventionTaskSummary | None = None
    workflow_status: PatientWorkflowStatusSummary | None = None
    attention_reason: str | None = None
    next_step: str | None = None
    next_step_reason: str | None = None
    next_step_reason_detail_label: str | None = None
    active_owner_label: str | None = None
    waiting_on_label: str | None = None
    care_gap_label: str | None = None
    blocking_issue_label: str | None = None
    resolution_target_label: str | None = None
    closure_readiness_label: str | None = None
    closure_readiness_reason_label: str | None = None
    resolution_confidence_label: str | None = None
    resolution_confidence_reason_label: str | None = None
    recommended_timeframe: str | None = None
    recommended_timeframe_reason_label: str | None = None
    workflow_age_label: str | None = None
    recent_change_label: str | None = None
    last_operational_change_label: str | None = None
    last_operational_change_reason_label: str | None = None
    staleness_indicator: str | None = None
    priority_band: str | None = None
    priority_reason: str | None = None
    status_snapshot: str | None = None
    status_snapshot_reason_label: str | None = None


class PatientQueueImpactSnapshot(BaseModel):
    patients_needing_attention: int = Field(default=0, ge=0)
    open_escalations: int = Field(default=0, ge=0)
    tasks_in_progress: int = Field(default=0, ge=0)
    completed_tasks_recently: int = Field(default=0, ge=0)
    completed_tasks_recently_window_days: int = Field(default=7, ge=1)
    operational_summary: str | None = None


class PatientTimelineWorklistSummaryResponse(BaseModel):
    items: list[PatientTimelineWorklistSummaryItem]
    total: int = Field(default=0, ge=0)
    impact_snapshot: PatientQueueImpactSnapshot = Field(default_factory=PatientQueueImpactSnapshot)
