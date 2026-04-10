from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.intervention_task import InterventionTaskPriority
from app.models.patient_signal import EscalationSeverity, SignalType


class WorkflowBootstrapCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    sex: str | None = Field(default=None, max_length=32)
    external_patient_id: str | None = Field(default=None, max_length=64)
    signal_type: SignalType = SignalType.MISSED_CHECK_IN
    signal_source: str | None = Field(default="admin_bootstrap", max_length=64)
    signal_value_numeric: float | None = None
    signal_value_text: str | None = Field(default=None, max_length=2000)
    unit: str | None = Field(default=None, max_length=32)
    recorded_at: datetime | None = None
    signal_notes: str | None = Field(default=None, max_length=2000)
    escalation_type: str = Field(default="clinical_review", max_length=64)
    escalation_severity: EscalationSeverity = EscalationSeverity.MEDIUM
    escalation_sla_due_at: datetime | None = None
    escalation_note: str | None = Field(default=None, max_length=2000)
    create_open_task: bool = True
    task_title: str | None = Field(default=None, max_length=255)
    task_description: str | None = Field(default=None, max_length=4000)
    task_priority: InterventionTaskPriority = InterventionTaskPriority.MEDIUM
    task_due_at: datetime | None = None
    task_assigned_user_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class WorkflowBootstrapCreateResponse(BaseModel):
    organization_id: UUID
    patient_id: UUID
    signal_id: UUID
    escalation_id: UUID
    status_event_id: UUID
    task_id: UUID | None
    patient_full_name: str
    signal_type: SignalType
    escalation_type: str
    escalation_severity: EscalationSeverity
    task_created: bool

    model_config = ConfigDict(from_attributes=True)
