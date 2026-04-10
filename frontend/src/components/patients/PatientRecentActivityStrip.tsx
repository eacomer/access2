import { formatDateTime, formatEventType, formatRelativeTimeCompact } from "../../lib/format";
import STATUS_LABELS from "../../lib/statusLabels";
import { describeWorkflowDriver, workflowSeverityToTone } from "../../lib/workflowStatus";
import type {
  EscalationStatus,
  PatientEscalationEvidence,
  PatientTimelineItem,
  PatientInterventionTaskSummary,
  PatientTimelineWorklistSummaryItem,
  PatientWorkflowStatusSummary,
} from "../../types/patient";

type Props = {
  latestEvent: PatientTimelineItem | null;
  summary: PatientTimelineWorklistSummaryItem | null;
  taskSummary?: PatientInterventionTaskSummary | null;
  escalationEvidence?: PatientEscalationEvidence | null;
  workflowStatus?: PatientWorkflowStatusSummary | null;
  activeEscalationStatus?: EscalationStatus | null;
};

type Cue = {
  id: string;
  label: string;
  value: string;
  detail?: string;
  tone?: "info" | "warning" | "alert";
};

const buildLastEventCue = (
  latestEvent: PatientTimelineItem | null,
  summary: PatientTimelineWorklistSummaryItem | null,
): Cue | null => {
  const eventType = latestEvent?.event_type ?? summary?.latest_event_type;
  const occurredAt = latestEvent?.occurred_at ?? summary?.latest_event_occurred_at;
  if (!eventType && !occurredAt) {
    return null;
  }
  return {
    id: "latest-event",
    label: STATUS_LABELS.latestEvent,
    value: eventType ? formatEventType(eventType) : "Recorded",
    detail: occurredAt
      ? `${formatRelativeTimeCompact(occurredAt)} · ${formatDateTime(occurredAt)}`
      : undefined,
  };
};

const buildTaskCue = (taskSummary: PatientInterventionTaskSummary | null): Cue | null => {
  if (!taskSummary) {
    return null;
  }
  if (taskSummary.overdue_task_count > 0) {
    return {
      id: "tasks-overdue",
      label: "Tasks",
      value: `${taskSummary.overdue_task_count} overdue`,
      tone: "alert",
    };
  }
  if (taskSummary.in_progress_task_count > 0) {
    return {
      id: "tasks-in-progress",
      label: "Tasks",
      value: `${taskSummary.in_progress_task_count} in progress`,
      tone: "info",
    };
  }
  if (taskSummary.open_task_count > 0) {
    const latestTaskTimestamp =
      taskSummary.latest_active_task_due_at ?? taskSummary.latest_active_task_created_at ?? null;
    return {
      id: "tasks-open",
      label: "Tasks",
      value: `${taskSummary.open_task_count} open`,
      tone: taskSummary.open_task_count > 3 ? "info" : undefined,
      detail: latestTaskTimestamp
        ? `Latest ${formatRelativeTimeCompact(latestTaskTimestamp)}`
        : undefined,
    };
  }

  const latestTitle = taskSummary.latest_active_task_title;
  if (latestTitle) {
    return {
      id: "tasks-cleared",
      label: "Tasks",
      value: "No active tasks",
      detail: `Last: ${latestTitle}`,
    };
  }
  return {
    id: "tasks-cleared",
    label: "Tasks",
    value: "No active tasks",
  };
};

const buildUnreadCue = (summary: PatientTimelineWorklistSummaryItem | null): Cue | null => {
  if (!summary?.has_unread_events || summary.unread_count <= 0) {
    return null;
  }
  return {
    id: "unread",
    label: STATUS_LABELS.unreadActivity,
    value: `${summary.unread_count} new`,
    tone: "info",
  };
};

const buildEscalationCue = (
  summary: PatientTimelineWorklistSummaryItem | null,
  evidence: PatientEscalationEvidence | null,
  activeEscalationStatus: EscalationStatus | null | undefined,
): Cue | null => {
  if (!summary && !evidence) {
    return null;
  }
  const overdue = evidence?.overdue_escalation_count ?? summary?.overdue_escalation_count ?? 0;
  const nextSla =
    evidence?.next_open_escalation_sla_due_at ?? summary?.next_escalation_sla_due_at ?? null;
  if (overdue > 0) {
    return {
      id: "escalation-overdue",
      label: "Escalations",
      value: `${overdue} overdue`,
      tone: "alert",
      detail: nextSla ? `Next SLA ${formatRelativeTimeCompact(nextSla)}` : undefined,
    };
  }
  const atRisk = evidence?.at_risk_escalation_count ?? summary?.at_risk_escalation_count ?? 0;
  if (atRisk > 0) {
    return {
      id: "escalation-at-risk",
      label: "Escalations",
      value: `${atRisk} at risk`,
      tone: "warning",
      detail: nextSla ? `Next SLA ${formatRelativeTimeCompact(nextSla)}` : undefined,
    };
  }
  const open = evidence?.open_escalation_count ?? summary?.open_escalation_count ?? 0;
  if (open > 0) {
    return {
      id: "escalation-open",
      label: "Escalations",
      value: `${open} active`,
      tone: "info",
    };
  }
  const resolvedStatus = activeEscalationStatus ?? evidence?.latest_open_escalation_status ?? null;
  if (resolvedStatus === "resolved") {
    return {
      id: "escalation-resolved",
      label: "Escalations",
      value: "Escalation resolved",
    };
  }
  if (resolvedStatus === "canceled") {
    return {
      id: "escalation-canceled",
      label: "Escalations",
      value: "Escalation closed",
    };
  }
  return {
    id: "escalation-clear",
    label: "Escalations",
    value: "No active escalations",
  };
};

const buildWorkflowCue = (
  workflowStatus: PatientWorkflowStatusSummary | null | undefined,
): Cue | null => {
  if (!workflowStatus) {
    return null;
  }
  return {
    id: "workflow-posture",
    label: "Workflow posture",
    value: workflowStatus.label,
    detail:
      workflowStatus.detail ??
      describeWorkflowDriver(workflowStatus.primary_driver) ??
      (workflowStatus.has_active_work ? "Active work in progress" : "Monitoring posture"),
    tone: workflowSeverityToTone(workflowStatus.severity),
  };
};

export default function PatientRecentActivityStrip({
  latestEvent,
  summary,
  taskSummary,
  escalationEvidence,
  workflowStatus,
  activeEscalationStatus,
}: Props) {
  const cues: Cue[] = [];
  const resolvedTaskSummary = taskSummary ?? summary?.task_summary ?? null;
  const taskCue = buildTaskCue(resolvedTaskSummary);
  if (taskCue) {
    cues.push(taskCue);
  }
  const lastEventCue = buildLastEventCue(latestEvent, summary);
  if (lastEventCue) {
    cues.push(lastEventCue);
  }
  const unreadCue = buildUnreadCue(summary);
  if (unreadCue) {
    cues.push(unreadCue);
  }
  const escalationCue = buildEscalationCue(summary, escalationEvidence ?? null, activeEscalationStatus);
  if (escalationCue) {
    cues.push(escalationCue);
  }
  const workflowCue = buildWorkflowCue(workflowStatus);
  if (workflowCue) {
    cues.push(workflowCue);
  }

  if (cues.length === 0) {
    return null;
  }

  return (
    <section className="patient-activity-strip" aria-label="Recent activity overview">
      {cues.map((cue) => (
        <div
          key={cue.id}
          className={`patient-activity-cue${cue.tone ? ` patient-activity-cue--${cue.tone}` : ""}`}
        >
          <span className="patient-activity-label">{cue.label}</span>
          <span className="patient-activity-value">{cue.value}</span>
          {cue.detail ? <span className="patient-activity-detail">{cue.detail}</span> : null}
        </div>
      ))}
    </section>
  );
}
