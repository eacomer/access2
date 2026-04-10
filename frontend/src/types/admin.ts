import type { InterventionTaskPriority } from "./patient";

export type WorkflowBootstrapSignalType =
  | "symptom_score"
  | "blood_pressure_systolic"
  | "blood_pressure_diastolic"
  | "weight_change"
  | "missed_check_in"
  | (string & {});

export type WorkflowBootstrapEscalationSeverity = "low" | "medium" | "high" | (string & {});

export interface WorkflowBootstrapCreateRequest {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex?: string | null;
  external_patient_id?: string | null;
  signal_type: WorkflowBootstrapSignalType;
  signal_source?: string | null;
  signal_value_numeric?: number | null;
  signal_value_text?: string | null;
  unit?: string | null;
  recorded_at?: string | null;
  signal_notes?: string | null;
  escalation_type?: string;
  escalation_severity: WorkflowBootstrapEscalationSeverity;
  escalation_sla_due_at?: string | null;
  escalation_note?: string | null;
  create_open_task?: boolean;
  task_title?: string | null;
  task_description?: string | null;
  task_priority?: InterventionTaskPriority;
  task_due_at?: string | null;
  task_assigned_user_id?: string | null;
}

export interface WorkflowBootstrapCreateResponse {
  organization_id: string;
  patient_id: string;
  signal_id: string;
  escalation_id: string;
  status_event_id: string;
  task_id: string | null;
  patient_full_name: string;
  signal_type: WorkflowBootstrapSignalType;
  escalation_type: string;
  escalation_severity: WorkflowBootstrapEscalationSeverity;
  task_created: boolean;
}
