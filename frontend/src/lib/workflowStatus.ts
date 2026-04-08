import type { PatientWorkflowStatusSummary } from "../types/patient";

export type WorkflowTone = "info" | "warning" | "alert";

export type WorkflowSeverityKey = "overdue" | "urgent" | "active" | "stable";

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
