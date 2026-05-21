from __future__ import annotations

from datetime import datetime
from typing import Any
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


class AccessTrackOutcomeEvidence(BaseModel):
    clinical_track: str
    qualifying_condition: str
    metric_name: str
    baseline_measure: float | str | None = None
    baseline_outcome_id: UUID | None = None
    baseline_observed_at: datetime | None = None
    follow_up_measure: float | str | None = None
    follow_up_outcome_id: UUID | None = None
    follow_up_observed_at: datetime | None = None
    outcome_status: str
    care_update_milestone: str | None = None
    care_update_id: UUID | None = None
    evidence_completeness_status: str


class InterventionOutcomeLink(BaseModel):
    intervention_task_id: UUID
    intervention_timestamp: datetime | None = None
    linked_outcome_ids: list[UUID] = Field(default_factory=list)
    linked_outcome_metric_names: list[str] = Field(default_factory=list)
    outcomes_after_intervention: bool
    first_outcome_lag_hours: float | None = None
    first_outcome_lag_days: float | None = None


class EscalationResolutionSummary(BaseModel):
    escalation_id: UUID
    resolved_at: datetime | None = None
    resolution_reason: str | None = None
    resolution_notes: str | None = None
    outcome_id: UUID | None = None
    care_update_id: UUID | None = None


class AccessCaseEscalationSummary(BaseModel):
    open_count: int = 0
    resolved_count: int = 0
    latest_escalation_id: UUID | None = None
    latest_status: str | None = None
    latest_triggered_at: datetime | None = None
    latest_resolution: EscalationResolutionSummary | None = None


class AccessCaseInterventionSummaryItem(BaseModel):
    intervention_task_id: UUID
    escalation_id: UUID | None = None
    status: str
    priority: str
    title: str
    created_at: datetime
    completed_at: datetime | None = None
    linked_outcome_ids: list[UUID] = Field(default_factory=list)


class AccessCaseCareUpdateSummary(BaseModel):
    care_update_id: UUID
    occurred_at: datetime
    care_update_type: str
    summary: str
    escalation_id: UUID | None = None
    intervention_task_id: UUID | None = None
    outcome_id: UUID | None = None


class AccessCaseEvidenceCompleteness(BaseModel):
    has_outcome: bool
    has_care_update: bool
    has_resolution_evidence: bool
    missing_components: list[str] = Field(default_factory=list)


class AccessReviewReadinessSummary(BaseModel):
    has_measured_outcome: bool
    has_care_update: bool
    has_resolution_evidence: bool
    has_open_work: bool
    latest_outcome_at: datetime | None = None
    latest_care_update_at: datetime | None = None
    latest_resolution_at: datetime | None = None
    readiness_status: str


class AccessReviewChecklistItem(BaseModel):
    key: str
    label: str
    status: str
    reason: str


class AccessReviewChecklist(BaseModel):
    overall_status: str
    ready_count: int = 0
    warning_count: int = 0
    missing_count: int = 0
    items: list[AccessReviewChecklistItem] = Field(default_factory=list)


class AccessReviewStateResponse(BaseModel):
    state: str
    label: str
    next_action: str
    is_actionable: bool
    is_approvable: bool
    requires_override_for_approval: bool
    approval_override_used: bool
    missing_checklist_items: list[str] = Field(default_factory=list)
    assigned_reviewer_user_id: UUID | None = None
    last_decision_at: datetime | None = None
    last_decision_by_user_id: UUID | None = None


class AccessReviewActionResponse(BaseModel):
    action: str
    reason: str
    priority: str


class AccessReviewAuditTimelineItemResponse(BaseModel):
    event_type: str
    occurred_at: datetime
    actor_user_id: UUID | None = None
    summary: str


class AccessCaseSummaryResponse(BaseModel):
    patient_id: UUID
    escalation_summary: AccessCaseEscalationSummary
    interventions: list[AccessCaseInterventionSummaryItem] = Field(default_factory=list)
    outcome_summaries: list[OutcomeMetricSummary] = Field(default_factory=list)
    access_track_outcome_evidence: list[AccessTrackOutcomeEvidence] = Field(default_factory=list)
    care_update_evidence: list[AccessCaseCareUpdateSummary] = Field(default_factory=list)
    latest_care_update: AccessCaseCareUpdateSummary | None = None
    evidence_completeness: AccessCaseEvidenceCompleteness
    review_readiness: AccessReviewReadinessSummary
    review_checklist: AccessReviewChecklist


class AccessEvidenceResponse(BaseModel):
    patient_id: UUID
    outcome_summaries: list[OutcomeMetricSummary] = Field(default_factory=list)
    access_track_outcome_evidence: list[AccessTrackOutcomeEvidence] = Field(default_factory=list)
    care_update_evidence: list[AccessCaseCareUpdateSummary] = Field(default_factory=list)
    intervention_outcome_links: list[InterventionOutcomeLink] = Field(default_factory=list)
    escalation_resolution_summaries: list[EscalationResolutionSummary] = Field(default_factory=list)
    review_readiness: AccessReviewReadinessSummary


class AccessReviewPacketResponse(BaseModel):
    patient_id: UUID
    generated_at: datetime
    review_readiness: AccessReviewReadinessSummary
    review_checklist: AccessReviewChecklist
    case_summary: AccessCaseSummaryResponse
    evidence_report: AccessEvidenceResponse


class AccessReviewPacketSnapshotResponse(BaseModel):
    id: UUID
    patient_id: UUID
    organization_id: UUID
    generated_at: datetime
    created_at: datetime
    updated_at: datetime
    review_readiness_status: str
    review_status: str
    reviewed_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    assigned_reviewer_user_id: UUID | None = None
    review_note: str | None = None
    review_state: AccessReviewStateResponse
    review_action: AccessReviewActionResponse | None = None
    audit_timeline: list[AccessReviewAuditTimelineItemResponse] | None = None
    packet_json: AccessReviewPacketResponse
    packet_markdown: str


class AccessReviewPacketSnapshotReviewUpdateRequest(BaseModel):
    review_status: str
    review_note: str | None = None
    decision_note: str | None = None
    override_missing_checklist: bool = False
    override_reason: str | None = None


class AccessReviewPacketSnapshotAssignmentUpdateRequest(BaseModel):
    assigned_reviewer_user_id: UUID | None = None


class AccessReviewPacketSnapshotEventResponse(BaseModel):
    id: UUID
    event_type: str
    actor_user_id: UUID | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AccessReviewPacketSnapshotEventListResponse(BaseModel):
    snapshot_id: UUID
    patient_id: UUID
    events: list[AccessReviewPacketSnapshotEventResponse] = Field(default_factory=list)


class AccessReviewPacketSnapshotAuditManifestResponse(BaseModel):
    snapshot_id: UUID
    patient_id: UUID
    review_status: str
    generated_from: str
    packet_json_sha256: str
    packet_markdown_sha256: str
    decision_event_count: int
    approval_event_id: UUID
    approval_override_used: bool


class AccessReviewPacketSnapshotAuditManifestVerifyRequest(BaseModel):
    audit_manifest: AccessReviewPacketSnapshotAuditManifestResponse


class AccessReviewPacketSnapshotAuditManifestMismatchResponse(BaseModel):
    field: str
    expected: str | int | bool
    actual: str | int | bool


class AccessReviewPacketSnapshotAuditManifestVerifyResponse(BaseModel):
    snapshot_id: UUID
    verified: bool
    mismatches: list[AccessReviewPacketSnapshotAuditManifestMismatchResponse] = Field(
        default_factory=list
    )
    expected_manifest: AccessReviewPacketSnapshotAuditManifestResponse


class AccessReviewPacketSnapshotAuditLifecycleCountsResponse(BaseModel):
    class PendingReviewAgeResponse(BaseModel):
        new_today_count: int = 0
        one_to_three_days_count: int = 0
        four_to_seven_days_count: int = 0
        over_seven_days_count: int = 0

    pending_unassigned_count: int = 0
    pending_assigned_ready_count: int = 0
    blocked_missing_evidence_count: int = 0
    approved_count: int = 0
    approved_with_override_count: int = 0
    rejected_count: int = 0
    approved_not_exported_count: int = 0
    exported_count: int = 0
    pending_review_age: PendingReviewAgeResponse = Field(default_factory=PendingReviewAgeResponse)


class AccessReviewPacketSnapshotExportMetadataResponse(BaseModel):
    document_title: str
    export_kind: str
    recommended_filename: str
    content_type: str
    source: str
    generated_at: datetime
    verification_endpoint: str
    verification_method: str


class AccessReviewPacketSnapshotAuditBundleResponse(BaseModel):
    snapshot_id: UUID
    patient_id: UUID
    organization_id: UUID
    review_status: str
    review_state: AccessReviewStateResponse
    approved_at: datetime
    approved_by_user_id: UUID | None = None
    approval_event: AccessReviewPacketSnapshotEventResponse
    snapshot_created_at: datetime
    assigned_reviewer_user_id: UUID | None = None
    packet_json: AccessReviewPacketResponse
    packet_markdown: str
    review_checklist: AccessReviewChecklist
    readiness_reasons: list["AccessReviewPacketPatientReadinessReasonResponse"] = Field(
        default_factory=list
    )
    audit_manifest: AccessReviewPacketSnapshotAuditManifestResponse
    export_metadata: AccessReviewPacketSnapshotExportMetadataResponse
    decision_events: list[AccessReviewPacketSnapshotEventResponse] = Field(default_factory=list)


class AccessReviewPacketSnapshotSummaryResponse(BaseModel):
    total: int
    pending_review: int
    approved: int
    rejected: int
    ready_for_review: int = 0
    active_open_work: int = 0
    incomplete: int = 0


class AccessReviewPacketSnapshotQueueSummaryResponse(BaseModel):
    class AuditReadinessRollupResponse(BaseModel):
        incomplete_count: int = 0
        review_ready_count: int = 0
        approved_not_exported_count: int = 0
        audit_ready_count: int = 0
        rejected_count: int = 0

    total: int
    review_status: dict[str, int] = Field(default_factory=dict)
    review_readiness_status: dict[str, int] = Field(default_factory=dict)
    assigned: int = 0
    unassigned: int = 0
    pending_review_assigned: int = 0
    pending_review_unassigned: int = 0
    pending_review_ready_for_review: int = 0
    pending_review_active_open_work: int = 0
    pending_review_incomplete: int = 0
    snapshot_audit_lifecycle: AccessReviewPacketSnapshotAuditLifecycleCountsResponse = Field(
        default_factory=AccessReviewPacketSnapshotAuditLifecycleCountsResponse
    )
    audit_readiness_rollup: AuditReadinessRollupResponse = Field(
        default_factory=AuditReadinessRollupResponse
    )


class AccessReviewPacketReviewerSummaryResponse(BaseModel):
    assigned_to_me_count: int = 0
    pending_assigned_ready_count: int = 0
    blocked_missing_evidence_count: int = 0
    oldest_pending_snapshot_created_at: datetime | None = None
    pending_review_age: AccessReviewPacketSnapshotAuditLifecycleCountsResponse.PendingReviewAgeResponse = (
        Field(
            default_factory=AccessReviewPacketSnapshotAuditLifecycleCountsResponse.PendingReviewAgeResponse
        )
    )


class AccessReviewPacketAuditReadinessItemResponse(BaseModel):
    patient_id: UUID
    latest_snapshot_id: UUID
    latest_snapshot_created_at: datetime
    review_status: str
    review_state: str
    completion_status: str
    assigned_reviewer_user_id: UUID | None = None
    next_step: AccessReviewPacketPatientNextStepResponse
    audit_bundle: AccessReviewPacketPatientAuditBundleStatusResponse


class AccessReviewPacketAuditReadinessListResponse(BaseModel):
    items: list[AccessReviewPacketAuditReadinessItemResponse] = Field(default_factory=list)
    total_count: int = 0
    limit: int = 50
    offset: int = 0
    status_counts: AccessReviewPacketSnapshotQueueSummaryResponse.AuditReadinessRollupResponse = Field(
        default_factory=AccessReviewPacketSnapshotQueueSummaryResponse.AuditReadinessRollupResponse
    )


class AccessReviewPacketPatientAuditBundleStatusResponse(BaseModel):
    available: bool = False
    exported: bool = False
    last_exported_at: datetime | None = None
    export_formats: list[str] = Field(default_factory=list)


class AccessReviewPacketPatientNextStepResponse(BaseModel):
    action: str
    reason: str
    priority: str


class AccessReviewPacketPatientCompletionSummaryResponse(BaseModel):
    status: str
    missing_evidence_count: int
    has_required_evidence: bool
    has_approval: bool
    has_export: bool
    reason: str


class AccessReviewPacketPatientReadinessReasonResponse(BaseModel):
    code: str
    severity: str
    label: str
    detail: str


class AccessReviewPacketPatientAuditStatusResponse(BaseModel):
    patient_id: UUID
    has_snapshot: bool
    latest_snapshot_id: UUID | None = None
    latest_snapshot_created_at: datetime | None = None
    review_status: str | None = None
    review_state: AccessReviewStateResponse | None = None
    assigned_reviewer_user_id: UUID | None = None
    review_action: AccessReviewActionResponse | None = None
    audit_bundle: AccessReviewPacketPatientAuditBundleStatusResponse = Field(
        default_factory=AccessReviewPacketPatientAuditBundleStatusResponse
    )
    next_step: AccessReviewPacketPatientNextStepResponse
    completion_summary: AccessReviewPacketPatientCompletionSummaryResponse
    readiness_reasons: list[AccessReviewPacketPatientReadinessReasonResponse] = Field(
        default_factory=list
    )


class AccessReviewPacketSnapshotPatientBacklogItem(BaseModel):
    patient_id: UUID
    latest_snapshot_id: UUID
    latest_snapshot_created_at: datetime
    latest_review_status: str
    latest_review_readiness_status: str
    review_state: AccessReviewStateResponse
    pending_review_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    total_snapshot_count: int = 0


class AccessReviewPacketPatientDrillInResponse(BaseModel):
    patient_id: UUID
    audit_status: AccessReviewPacketPatientAuditStatusResponse
    snapshots: list[AccessReviewPacketSnapshotResponse] = Field(default_factory=list)
