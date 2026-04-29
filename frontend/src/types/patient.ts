export type EscalationStatus = "open" | "in_progress" | "resolved" | "canceled";

export type InterventionTaskPriority = "low" | "medium" | "high" | "urgent";

export type WorkflowPrimaryDriver = "task" | "escalation" | "monitoring" | (string & {});

export type WorkflowSeverity = "overdue" | "urgent" | "active" | "stable" | (string & {});

export interface PatientWorkflowStatusSummary {
  status_key: string;
  label: string;
  has_active_work: boolean;
  primary_driver: WorkflowPrimaryDriver;
  severity?: WorkflowSeverity | null;
  detail?: string | null;
}

export interface PatientInterventionEvidenceSummaryItem {
  title: string;
  status: string | null;
  occurred_at: string | null;
  detail: string | null;
}

export interface PatientInterventionEvidenceSummary {
  total_escalations: number;
  open_escalations: number;
  total_tasks: number;
  open_tasks: number;
  in_progress_tasks: number;
  completed_tasks: number;
  canceled_tasks: number;
  recent_trigger_reasons: PatientInterventionEvidenceSummaryItem[];
  recent_completed_interventions: PatientInterventionEvidenceSummaryItem[];
  current_open_work: PatientInterventionEvidenceSummaryItem[];
  evidence_event_count: number;
}

export interface PatientAttentionSummary {
  why_now: string;
  primary_driver: WorkflowPrimaryDriver | null;
  recommended_next_action: string;
  supporting_evidence: string[];
  urgency_level: WorkflowSeverity | null;
}

export interface PatientInterventionTaskSummary {
  open_task_count: number;
  in_progress_task_count: number;
  overdue_task_count: number;
  latest_active_task_id: string | null;
  latest_active_task_title: string | null;
  latest_active_task_status: string | null;
  latest_active_task_priority: InterventionTaskPriority | null;
  latest_active_task_due_at: string | null;
  latest_active_task_created_at: string | null;
}

export interface PatientTimelineWorklistSummaryItem {
  patient_id: string;
  patient_display_name: string;
  has_unread_events: boolean;
  unread_count: number;
  total_events: number;
  latest_event_id: string | null;
  latest_event_type: string | null;
  latest_event_occurred_at: string | null;
  latest_event_title: string | null;
  latest_unread_event_id: string | null;
  latest_unread_event_type: string | null;
  latest_unread_event_occurred_at: string | null;
  oldest_unread_event_id: string | null;
  oldest_unread_event_occurred_at: string | null;
  open_escalation_count: number;
  overdue_escalation_count: number;
  at_risk_escalation_count: number;
  highest_escalation_priority: string | null;
  next_escalation_sla_due_at: string | null;
  latest_open_escalation_id: string | null;
  task_summary?: PatientInterventionTaskSummary | null;
  workflow_status?: PatientWorkflowStatusSummary | null;
  attention_reason?: string | null;
  next_step?: string | null;
  next_step_reason?: string | null;
  next_step_reason_detail_label?: string | null;
  active_owner_label?: string | null;
  waiting_on_label?: string | null;
  care_gap_label?: string | null;
  blocking_issue_label?: string | null;
  resolution_target_label?: string | null;
  closure_readiness_label?: string | null;
  closure_readiness_reason_label?: string | null;
  resolution_confidence_label?: string | null;
  resolution_confidence_reason_label?: string | null;
  recommended_timeframe?: string | null;
  recommended_timeframe_reason_label?: string | null;
  workflow_age_label?: string | null;
  recent_change_label?: string | null;
  last_operational_change_label?: string | null;
  last_operational_change_reason_label?: string | null;
  staleness_indicator?: string | null;
  priority_band?: string | null;
  priority_reason?: string | null;
  status_snapshot?: string | null;
  status_snapshot_reason_label?: string | null;
}

export interface PatientQueueImpactSnapshot {
  patients_needing_attention: number;
  open_escalations: number;
  tasks_in_progress: number;
  completed_tasks_recently: number;
  completed_tasks_recently_window_days: number;
  operational_summary?: string | null;
}

export interface Patient {
  id: string;
  organization_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: string | null;
  external_patient_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PatientTimelineWorklistSummaryResponse {
  items: PatientTimelineWorklistSummaryItem[];
  total: number;
  impact_snapshot?: PatientQueueImpactSnapshot | null;
}

export interface PatientTimelineItem {
  event_id: string;
  event_type: string;
  occurred_at: string;
  patient_id: string;
  organization_id: string;
  source_id: string;
  source_kind: string;
  display_title: string;
  display_text: string | null;
  status: string | null;
  priority: string | null;
  authored_by_user_id: string | null;
  actor_user_id: string | null;
  related_escalation_id: string | null;
  related_task_id: string | null;
  related_outcome_id: string | null;
  metadata: Record<string, unknown>;
}

export interface PatientTimelineListResponse {
  items: PatientTimelineItem[];
  total: number;
  limit: number;
  next_cursor_occurred_at: string | null;
  next_cursor_event_id: string | null;
  has_more: boolean;
}

export interface PatientTimelineFilters {
  event_types?: string[];
  occurred_after?: string | null;
  occurred_before?: string | null;
  related_escalation_id?: string | null;
  related_task_id?: string | null;
  task_statuses?: string[];
  include_only_open_work?: boolean;
}

export interface PatientEscalationEvidence {
  has_open_escalation: boolean;
  open_escalation_count: number;
  overdue_escalation_count: number;
  at_risk_escalation_count: number;
  highest_open_escalation_priority: string | null;
  next_open_escalation_sla_due_at: string | null;
  latest_open_escalation_id: string | null;
  latest_open_escalation_status: EscalationStatus | null;
  latest_open_escalation_created_at: string | null;
  latest_escalation_event_id: string | null;
  latest_escalation_event_type: string | null;
  latest_escalation_event_occurred_at: string | null;
}

export interface PatientTimelineDetailResponse {
  item: PatientTimelineItem;
  escalation_evidence: PatientEscalationEvidence | null;
  task_summary?: PatientInterventionTaskSummary | null;
  workflow_status?: PatientWorkflowStatusSummary | null;
  intervention_evidence_summary?: PatientInterventionEvidenceSummary | null;
  attention_summary?: PatientAttentionSummary | null;
  status_snapshot?: string | null;
  status_snapshot_reason_label?: string | null;
  care_gap_label?: string | null;
  blocking_issue_label?: string | null;
  resolution_target_label?: string | null;
  closure_readiness_label?: string | null;
  closure_readiness_reason_label?: string | null;
  resolution_confidence_label?: string | null;
  resolution_confidence_reason_label?: string | null;
  active_owner_label?: string | null;
  waiting_on_label?: string | null;
  next_step_reason_detail_label?: string | null;
  last_operational_change_label?: string | null;
  last_operational_change_reason_label?: string | null;
  recommended_timeframe_reason_label?: string | null;
}

export interface PatientEscalation {
  id: string;
  organization_id: string;
  patient_id: string;
  enrollment_id: string | null;
  signal_id: string | null;
  escalation_type: string;
  status: EscalationStatus;
  severity: string;
  triggered_at: string;
  in_progress_at: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  canceled_at: string | null;
  cancellation_notes: string | null;
  sla_due_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface InterventionTask {
  id: string;
  organization_id: string;
  patient_id: string;
  enrollment_id: string | null;
  escalation_id: string;
  assigned_user_id: string | null;
  created_by_user_id: string;
  title: string;
  description: string | null;
  status: string;
  priority: InterventionTaskPriority;
  due_at: string | null;
  completed_at: string | null;
  completed_by_user_id: string | null;
  completion_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface InterventionTaskCreateRequest {
  title: string;
  description?: string | null;
  priority?: InterventionTaskPriority;
  due_at?: string | null;
  assigned_user_id?: string | null;
}

export type ReviewPacketReviewStatus = "pending_review" | "approved" | "rejected";

export type ReviewStateValue =
  | "pending_unassigned"
  | "pending_assigned_ready"
  | "blocked_missing_evidence"
  | "approved"
  | "approved_with_override"
  | "rejected";

export type ReviewActionValue = "ready_to_review" | "missing_evidence" | "stale_review";

export type ReviewActionPriority = "normal" | "high";

export interface ReviewState {
  state: ReviewStateValue;
  label: string;
  next_action: string;
  is_actionable: boolean;
  is_approvable: boolean;
  requires_override_for_approval: boolean;
  approval_override_used: boolean;
  missing_checklist_items: string[];
  assigned_reviewer_user_id: string | null;
  last_decision_at: string | null;
  last_decision_by_user_id: string | null;
}

export interface ReviewAction {
  action: ReviewActionValue;
  reason: string;
  priority: ReviewActionPriority;
}

export type AuditReadinessStatus =
  | "incomplete"
  | "review_ready"
  | "approved_not_exported"
  | "audit_ready"
  | "rejected";

export interface AuditReadinessStatusCounts {
  incomplete_count: number;
  review_ready_count: number;
  approved_not_exported_count: number;
  audit_ready_count: number;
  rejected_count: number;
}

export type PatientAuditStatusNextStepAction =
  | "create_snapshot"
  | "assign_reviewer"
  | "complete_missing_evidence"
  | "review_snapshot"
  | "export_audit_bundle"
  | "no_action_needed";

export interface PatientAuditStatusNextStep {
  action: PatientAuditStatusNextStepAction;
  reason: string;
  priority: ReviewActionPriority;
}

export interface PatientAuditStatusCompletionSummary {
  status: "not_started" | AuditReadinessStatus;
  missing_evidence_count: number;
  has_required_evidence: boolean;
  has_approval: boolean;
  has_export: boolean;
  reason: string;
}

export interface PatientAuditBundleStatus {
  available: boolean;
  exported: boolean;
  last_exported_at: string | null;
  export_formats: string[];
}

export interface PatientAuditStatus {
  patient_id: string;
  has_snapshot: boolean;
  latest_snapshot_id: string | null;
  latest_snapshot_created_at: string | null;
  review_status: ReviewPacketReviewStatus | null;
  review_state: ReviewState | null;
  assigned_reviewer_user_id: string | null;
  review_action: ReviewAction | null;
  audit_bundle: PatientAuditBundleStatus;
  next_step: PatientAuditStatusNextStep;
  completion_summary: PatientAuditStatusCompletionSummary;
}

export interface AuditReadinessItem {
  patient_id: string;
  latest_snapshot_id: string;
  latest_snapshot_created_at: string;
  review_status: ReviewPacketReviewStatus;
  review_state: ReviewStateValue;
  completion_status: AuditReadinessStatus;
  assigned_reviewer_user_id: string | null;
  next_step: PatientAuditStatusNextStep;
  audit_bundle: PatientAuditBundleStatus;
}

export interface AuditReadinessResponse {
  items: AuditReadinessItem[];
  total_count: number;
  limit: number;
  offset: number;
  status_counts: AuditReadinessStatusCounts;
}

export interface PendingReviewAgeCounts {
  new_today_count: number;
  one_to_three_days_count: number;
  four_to_seven_days_count: number;
  over_seven_days_count: number;
}

export interface SnapshotAuditLifecycleCounts {
  pending_unassigned_count: number;
  pending_assigned_ready_count: number;
  blocked_missing_evidence_count: number;
  approved_count: number;
  approved_with_override_count: number;
  rejected_count: number;
  approved_not_exported_count: number;
  exported_count: number;
  pending_review_age: PendingReviewAgeCounts;
}

export interface ReviewPacketQueueSummary {
  total: number;
  review_status: Record<string, number>;
  review_readiness_status: Record<string, number>;
  assigned: number;
  unassigned: number;
  pending_review_assigned: number;
  pending_review_unassigned: number;
  pending_review_ready_for_review: number;
  pending_review_active_open_work: number;
  pending_review_incomplete: number;
  snapshot_audit_lifecycle: SnapshotAuditLifecycleCounts;
  audit_readiness_rollup: AuditReadinessStatusCounts;
}

export interface ReviewerMySummary {
  assigned_to_me_count: number;
  pending_assigned_ready_count: number;
  blocked_missing_evidence_count: number;
  oldest_pending_snapshot_created_at: string | null;
  pending_review_age: PendingReviewAgeCounts;
}

export interface ReviewPacketAuditTimelineItem {
  event_type: string;
  occurred_at: string;
  actor_user_id: string | null;
  summary: string;
}

export interface ReviewPacketSnapshot {
  id: string;
  patient_id: string;
  organization_id: string;
  generated_at: string;
  created_at: string;
  updated_at: string;
  review_readiness_status: string;
  review_status: ReviewPacketReviewStatus;
  reviewed_at: string | null;
  reviewed_by_user_id: string | null;
  assigned_reviewer_user_id: string | null;
  review_note: string | null;
  review_state: ReviewState;
  review_action: ReviewAction | null;
  audit_timeline: ReviewPacketAuditTimelineItem[] | null;
  packet_json: Record<string, unknown>;
  packet_markdown: string;
}

export interface PatientBacklogDrillInResponse {
  patient_id: string;
  audit_status: PatientAuditStatus;
  snapshots: ReviewPacketSnapshot[];
}
