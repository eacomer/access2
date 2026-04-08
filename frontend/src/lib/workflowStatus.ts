import type {
  PatientInterventionTaskSummary,
  PatientTimelineWorklistSummaryItem,
  PatientWorkflowStatusSummary,
} from "../types/patient";

export type WorkflowTone = "info" | "warning" | "alert";

export type WorkflowSeverityKey = "overdue" | "urgent" | "active" | "stable";

const WORKFLOW_SEVERITY_ORDER: WorkflowSeverityKey[] = ["overdue", "urgent", "active", "stable"];

export const describeWorkflowDriver = (driver?: string | null) => {
  if (!driver) {
    return null;
  }
  if (driver === "task") {
    return "Task-driven posture";
  }
  if (driver === "escalation") {
    return "Escalation-driven posture";
  }
  if (driver === "monitoring") {
    return "Monitoring posture";
  }
  return `${driver.charAt(0).toUpperCase()}${driver.slice(1)} posture`;
};

export const workflowSeverityToTone = (severity?: string | null): WorkflowTone | undefined => {
  if (!severity) {
    return undefined;
  }
  if (severity === "overdue") {
    return "alert";
  }
  if (severity === "urgent") {
    return "warning";
  }
  if (severity === "active") {
    return "info";
  }
  return undefined;
};

export const workflowSeverityToBadgeVariant = (severity?: string | null) => {
  if (!severity) {
    return "badge--info";
  }
  if (severity === "overdue") {
    return "badge--critical";
  }
  if (severity === "urgent") {
    return "badge--warning";
  }
  if (severity === "active") {
    return "badge--info";
  }
  return "badge--positive";
};

export const getWorkflowSeverityKey = (
  status?: PatientWorkflowStatusSummary | null,
): WorkflowSeverityKey | null => {
  if (!status) {
    return null;
  }
  const severity = status.severity ?? (status.has_active_work ? "active" : "stable");
  if (severity === "overdue") {
    return "overdue";
  }
  if (severity === "urgent") {
    return "urgent";
  }
  if (severity === "active") {
    return status.has_active_work ? "active" : "stable";
  }
  if (severity === "stable") {
    return "stable";
  }
  return status.has_active_work ? "active" : "stable";
};

const getSeverityRank = (status?: PatientWorkflowStatusSummary | null) => {
  const key = getWorkflowSeverityKey(status);
  if (!key) {
    return WORKFLOW_SEVERITY_ORDER.length;
  }
  return WORKFLOW_SEVERITY_ORDER.indexOf(key);
};

const getDriverRank = (driver?: string | null) => {
  if (driver === "escalation") {
    return 0;
  }
  if (driver === "task") {
    return 1;
  }
  if (driver === "monitoring") {
    return 2;
  }
  return 3;
};

export const compareWorkflowStatuses = (
  a: PatientWorkflowStatusSummary | null | undefined,
  b: PatientWorkflowStatusSummary | null | undefined,
): number => {
  const severityRankDiff = getSeverityRank(a) - getSeverityRank(b);
  if (severityRankDiff !== 0) {
    return severityRankDiff;
  }
  const driverRankDiff = getDriverRank(a?.primary_driver) - getDriverRank(b?.primary_driver);
  if (driverRankDiff !== 0) {
    return driverRankDiff;
  }
  const activeA = Boolean(a?.has_active_work);
  const activeB = Boolean(b?.has_active_work);
  if (activeA !== activeB) {
    return activeA ? -1 : 1;
  }
  return 0;
};

const pluralize = (count: number, singular: string, plural?: string) => {
  const resolvedPlural = plural ?? `${singular}s`;
  return `${count} ${count === 1 ? singular : resolvedPlural}`;
};

const buildFallbackStatus = (config: {
  key: string;
  label: string;
  driver: string;
  severity: WorkflowSeverityKey;
  detail?: string | null;
  active: boolean;
}): PatientWorkflowStatusSummary => ({
  status_key: config.key,
  label: config.label,
  primary_driver: config.driver,
  severity: config.severity,
  detail: config.detail ?? null,
  has_active_work: config.active,
});

const hasTasks = (summary: PatientInterventionTaskSummary | null | undefined) =>
  Boolean(summary && summary.open_task_count > 0);

export const inferWorkflowStatusSummary = (
  summary: PatientTimelineWorklistSummaryItem,
): PatientWorkflowStatusSummary | null => {
  const taskSummary = summary.task_summary ?? null;
  if (taskSummary?.overdue_task_count && taskSummary.overdue_task_count > 0) {
    return buildFallbackStatus({
      key: "fallback_task_overdue",
      label: `${pluralize(taskSummary.overdue_task_count, "task")} overdue`,
      driver: "task",
      severity: "overdue",
      detail: "Derived from active task load",
      active: true,
    });
  }
  if (summary.overdue_escalation_count > 0) {
    return buildFallbackStatus({
      key: "fallback_escalation_overdue",
      label: `${pluralize(summary.overdue_escalation_count, "escalation")} overdue`,
      driver: "escalation",
      severity: "overdue",
      detail: "Derived from escalation evidence",
      active: true,
    });
  }
  if (summary.at_risk_escalation_count > 0) {
    return buildFallbackStatus({
      key: "fallback_escalation_at_risk",
      label: `${pluralize(summary.at_risk_escalation_count, "escalation")} at risk`,
      driver: "escalation",
      severity: "urgent",
      detail: "Escalations approaching SLA breach",
      active: true,
    });
  }
  if (taskSummary?.in_progress_task_count && taskSummary.in_progress_task_count > 0) {
    return buildFallbackStatus({
      key: "fallback_task_in_progress",
      label: `${pluralize(taskSummary.in_progress_task_count, "task")} in progress`,
      driver: "task",
      severity: "active",
      detail: "Derived from task progress state",
      active: true,
    });
  }
  if (hasTasks(taskSummary)) {
    return buildFallbackStatus({
      key: "fallback_task_open",
      label: `${pluralize(taskSummary?.open_task_count ?? 0, "open task")}`,
      driver: "task",
      severity: "active",
      detail: "Derived from task load",
      active: true,
    });
  }
  if (summary.open_escalation_count > 0) {
    return buildFallbackStatus({
      key: "fallback_escalation_open",
      label: `${pluralize(summary.open_escalation_count, "escalation")} active`,
      driver: "escalation",
      severity: "active",
      detail: "Derived from escalation evidence",
      active: true,
    });
  }
  if (summary.has_unread_events && summary.unread_count > 0) {
    return buildFallbackStatus({
      key: "fallback_unread_monitoring",
      label: `${pluralize(summary.unread_count, "unread update")}`,
      driver: "monitoring",
      severity: "active",
      detail: "Unread timeline activity",
      active: true,
    });
  }
  return buildFallbackStatus({
    key: "fallback_monitoring",
    label: "Monitoring",
    driver: "monitoring",
    severity: "stable",
    detail: "No active tasks or escalations",
    active: false,
  });
};
