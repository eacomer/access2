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
}

export interface PatientTimelineWorklistSummaryResponse {
  items: PatientTimelineWorklistSummaryItem[];
  total: number;
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

export interface PatientEscalationEvidence {
  has_open_escalation: boolean;
  open_escalation_count: number;
  overdue_escalation_count: number;
  at_risk_escalation_count: number;
  highest_open_escalation_priority: string | null;
  next_open_escalation_sla_due_at: string | null;
  latest_open_escalation_id: string | null;
  latest_open_escalation_status: string | null;
  latest_open_escalation_created_at: string | null;
  latest_escalation_event_id: string | null;
  latest_escalation_event_type: string | null;
  latest_escalation_event_occurred_at: string | null;
}

export interface PatientTimelineDetailResponse {
  item: PatientTimelineItem;
  escalation_evidence: PatientEscalationEvidence | null;
}
