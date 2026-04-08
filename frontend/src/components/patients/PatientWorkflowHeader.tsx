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

type HeaderChip = {
  id: string;
  label: string;
  value: string;
  tone?: "info" | "warning" | "alert";
};

type MetadataItem = {
  id: string;
  label: string;
  value: string;
};

type InsightCard = {
  id: string;
  label: string;
  value: string;
  detail?: string;
  tone?: "info" | "warning" | "alert";
};

type Props = {
  patientName: string;
  patientId: string;
  summary: PatientTimelineWorklistSummaryItem | null;
  evidence: PatientEscalationEvidence | null;
  taskSummary?: PatientInterventionTaskSummary | null;
  workflowStatus?: PatientWorkflowStatusSummary | null;
  queueViewName?: string;
  queueFilterSummary?: string | null;
  hasQueueReturnContext?: boolean;
  latestEvent: PatientTimelineItem | null;
  activeEscalationStatus?: EscalationStatus | null;
};

const pluralize = (count: number, singular: string, plural?: string) => {
  if (!Number.isFinite(count)) {
    return singular;
  }
  const resolvedPlural = plural ?? `${singular}s`;
  return `${count} ${count === 1 ? singular : resolvedPlural}`;
};

const humanizeStatus = (value?: string | null) => {
  if (!value) {
    return null;
  }
  return value
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
};

const buildLegacySubtitleParts = (
  summary: PatientTimelineWorklistSummaryItem | null,
  evidence: PatientEscalationEvidence | null,
  taskSummary: PatientInterventionTaskSummary | null,
) => {
  const parts: string[] = [];
  if (taskSummary?.overdue_task_count) {
    parts.push(pluralize(taskSummary.overdue_task_count, "overdue task"));
  } else if (taskSummary?.open_task_count) {
    parts.push(pluralize(taskSummary.open_task_count, "open task"));
  }
  if (taskSummary?.in_progress_task_count) {
    parts.push(
      pluralize(taskSummary.in_progress_task_count, "task in progress", "tasks in progress"),
    );
  }
  if (summary?.total_events) {
    parts.push(pluralize(summary.total_events, "recorded event"));
  }
  if (summary?.has_unread_events && summary.unread_count > 0) {
    parts.push(pluralize(summary.unread_count, "unread event"));
  }
  if (summary?.open_escalation_count) {
    parts.push(pluralize(summary.open_escalation_count, "open escalation"));
  }
  const status = humanizeStatus(evidence?.latest_open_escalation_status);
  if (status) {
    parts.push(`Escalation ${status.toLowerCase()}`);
  }
  return parts;
};

const buildSubtitle = (
  summary: PatientTimelineWorklistSummaryItem | null,
  evidence: PatientEscalationEvidence | null,
  taskSummary: PatientInterventionTaskSummary | null,
  workflowStatus: PatientWorkflowStatusSummary | null,
): string => {
  const legacyParts = buildLegacySubtitleParts(summary, evidence, taskSummary);
  if (workflowStatus) {
    const parts = [workflowStatus.label];
    if (workflowStatus.detail) {
      parts.push(workflowStatus.detail);
    }
    if (workflowStatus.has_active_work) {
      const driver = describeWorkflowDriver(workflowStatus.primary_driver);
      if (driver) {
        parts.push(driver);
      }
    } else {
      parts.push("Monitoring posture");
    }
    if (!workflowStatus.detail && legacyParts.length > 0) {
      parts.push(legacyParts.join(" • "));
    }
    return parts.filter(Boolean).join(" • ");
  }
  if (legacyParts.length === 0) {
    return "Escalation-aware detail for the selected patient.";
  }
  return legacyParts.join(" • ");
};

const buildMetadata = (
  patientId: string,
  summary: PatientTimelineWorklistSummaryItem | null,
  taskSummary: PatientInterventionTaskSummary | null,
): MetadataItem[] => {
  const items: MetadataItem[] = [
    {
      id: "patient-id",
      label: "Patient ID",
      value: patientId,
    },
  ];
  if (taskSummary?.open_task_count || taskSummary?.overdue_task_count) {
    const overdueLabel =
      taskSummary.overdue_task_count && taskSummary.overdue_task_count > 0
        ? `${taskSummary.overdue_task_count} overdue`
        : null;
    const openLabel =
      taskSummary.open_task_count && taskSummary.open_task_count > 0
        ? `${taskSummary.open_task_count} open`
        : null;
    items.push({
      id: "tasks-count",
      label: "Task load",
      value: [overdueLabel, openLabel].filter(Boolean).join(" • ") || "No active tasks",
    });
  }

  if (summary?.latest_event_type) {
    items.push({
      id: "latest-type",
      label: "Latest event type",
      value: formatEventType(summary.latest_event_type),
    });
  }

  if (summary?.latest_event_occurred_at) {
    items.push({
      id: "latest-event",
      label: "Latest event at",
      value: formatDateTime(summary.latest_event_occurred_at),
    });
  }

  if (taskSummary?.latest_active_task_title) {
    items.push({
      id: "latest-task-title",
      label: "Active task",
      value: taskSummary.latest_active_task_title,
    });
  }
  if (taskSummary?.latest_active_task_due_at) {
    items.push({
      id: "latest-task-due",
      label: "Task due",
      value: `${formatRelativeTimeCompact(taskSummary.latest_active_task_due_at)} · ${formatDateTime(taskSummary.latest_active_task_due_at)}`,
    });
  } else if (taskSummary?.latest_active_task_created_at) {
    items.push({
      id: "latest-task-recorded",
      label: "Task recorded",
      value: `${formatRelativeTimeCompact(taskSummary.latest_active_task_created_at)} · ${formatDateTime(taskSummary.latest_active_task_created_at)}`,
    });
  }

  return items;
};

const buildChips = (
  summary: PatientTimelineWorklistSummaryItem | null,
  evidence: PatientEscalationEvidence | null,
  taskSummary: PatientInterventionTaskSummary | null,
  workflowStatus: PatientWorkflowStatusSummary | null,
): HeaderChip[] => {
  const chips: HeaderChip[] = [];

  if (workflowStatus) {
    chips.push({
      id: "workflow-posture",
      label: describeWorkflowDriver(workflowStatus.primary_driver) ?? "Workflow posture",
      value: workflowStatus.label,
      tone: workflowSeverityToTone(workflowStatus.severity),
    });
  }

  if (taskSummary?.overdue_task_count && taskSummary.overdue_task_count > 0) {
    chips.push({
      id: "tasks-overdue",
      label: "Tasks overdue",
      value: String(taskSummary.overdue_task_count),
      tone: "alert",
    });
  } else if (taskSummary?.open_task_count && taskSummary.open_task_count > 0) {
    chips.push({
      id: "tasks-open",
      label: "Open tasks",
      value: String(taskSummary.open_task_count),
      tone: taskSummary.open_task_count > 3 ? "info" : undefined,
    });
  }

  if (summary?.has_unread_events && summary.unread_count > 0) {
    chips.push({
      id: "unread",
      label: STATUS_LABELS.unreadActivity,
      value: String(summary.unread_count),
      tone: "info",
    });
  }

  if (summary?.open_escalation_count && summary.open_escalation_count > 0) {
    chips.push({
      id: "open-escalations",
      label: STATUS_LABELS.activeEscalations,
      value: String(summary.open_escalation_count),
    });
  }

  if (summary?.at_risk_escalation_count && summary.at_risk_escalation_count > 0) {
    chips.push({
      id: "at-risk",
      label: STATUS_LABELS.slaAtRisk,
      value: String(summary.at_risk_escalation_count),
      tone: "warning",
    });
  }

  if (summary?.overdue_escalation_count && summary.overdue_escalation_count > 0) {
    chips.push({
      id: "overdue",
      label: STATUS_LABELS.slaOverdue,
      value: String(summary.overdue_escalation_count),
      tone: "alert",
    });
  }

  const status = humanizeStatus(evidence?.latest_open_escalation_status);
  if (status) {
    chips.push({
      id: "status",
      label: STATUS_LABELS.activeEscalation,
      value: status,
      tone: evidence?.latest_open_escalation_status === "overdue" ? "alert" : undefined,
    });
  }

  const prioritized = chips.filter((chip) => chip.value.trim().length > 0);
  return prioritized.slice(0, 4);
};

const buildQueueInsight = (
  queueViewName?: string,
  queueFilterSummary?: string | null,
  hasQueueReturnContext?: boolean,
): InsightCard | null => {
  if (!queueViewName && !queueFilterSummary && !hasQueueReturnContext) {
    return null;
  }
  const label = hasQueueReturnContext ? "Queue return" : "Queue mode";
  const value = queueViewName
    ? hasQueueReturnContext
      ? `Back to ${queueViewName}`
      : queueViewName
    : "Patient queue";
  let detail: string | undefined;
  if (queueFilterSummary && queueFilterSummary.length > 0) {
    detail = hasQueueReturnContext
      ? `Filters preserved · ${queueFilterSummary}`
      : queueFilterSummary;
  } else if (hasQueueReturnContext) {
    detail = "Return context preserved";
  } else if (queueViewName) {
    detail = "Direct view";
  }
  return {
    id: "queue-context",
    label,
    value,
    detail,
    tone: hasQueueReturnContext ? "info" : undefined,
  };
};

const buildEscalationInsight = (
  summary: PatientTimelineWorklistSummaryItem | null,
  evidence: PatientEscalationEvidence | null,
  activeEscalationStatus?: EscalationStatus | null,
): InsightCard | null => {
  const overdue = evidence?.overdue_escalation_count ?? summary?.overdue_escalation_count ?? 0;
  const atRisk = evidence?.at_risk_escalation_count ?? summary?.at_risk_escalation_count ?? 0;
  const open = evidence?.open_escalation_count ?? summary?.open_escalation_count ?? 0;
  const status = humanizeStatus(activeEscalationStatus ?? evidence?.latest_open_escalation_status);
  const slaDue =
    evidence?.next_open_escalation_sla_due_at ?? summary?.next_escalation_sla_due_at ?? null;

  let tone: InsightCard["tone"];
  let value = "All clear";
  if (overdue > 0) {
    tone = "alert";
    value = pluralize(overdue, "overdue escalation");
  } else if (atRisk > 0) {
    tone = "warning";
    value = pluralize(atRisk, "at-risk escalation");
  } else if (open > 0) {
    tone = "info";
    value = pluralize(open, "open escalation");
  } else if (status) {
    value = `Escalation ${status.toLowerCase()}`;
  }

  const detail = slaDue ? `Next SLA ${formatRelativeTimeCompact(slaDue)}` : status ?? undefined;
  return {
    id: "escalation",
    label: "Escalation evidence",
    value,
    detail,
    tone,
  };
};

const buildWorkInsight = (
  summary: PatientTimelineWorklistSummaryItem | null,
  taskSummary: PatientInterventionTaskSummary | null,
  latestEvent: PatientTimelineItem | null,
  workflowStatus: PatientWorkflowStatusSummary | null,
): InsightCard | null => {
  if (taskSummary) {
    const overdueTasks = taskSummary.overdue_task_count;
    const inProgress = taskSummary.in_progress_task_count;
    const openTasks = taskSummary.open_task_count;
    const latestTitle = taskSummary.latest_active_task_title;
    const timingDetail =
      taskSummary.latest_active_task_due_at ??
      taskSummary.latest_active_task_created_at ??
      latestEvent?.occurred_at ??
      null;
    const detailParts = [];
    if (latestTitle) {
      detailParts.push(latestTitle);
    }
    if (timingDetail) {
      detailParts.push(formatRelativeTimeCompact(timingDetail));
    }
    const detail = detailParts.join(" · ") || undefined;

    if (overdueTasks && overdueTasks > 0) {
      return {
        id: "tasks-overdue",
        label: "Active work",
        value: `${pluralize(overdueTasks, "task")} overdue`,
        detail,
        tone: "alert",
      };
    }
    if (inProgress && inProgress > 0) {
      return {
        id: "tasks-progress",
        label: "Active work",
        value: pluralize(inProgress, "task in progress", "tasks in progress"),
        detail,
        tone: "info",
      };
    }
    if (openTasks && openTasks > 0) {
      return {
        id: "tasks-open",
        label: "Active work",
        value: pluralize(openTasks, "open task"),
        detail,
      };
    }
  }

  const unread = summary?.has_unread_events ? summary.unread_count : 0;
  const latestUnreadAt = summary?.latest_unread_event_occurred_at;
  if (latestEvent?.related_task_id) {
    const detailParts = [
      formatEventType(latestEvent.event_type),
      formatRelativeTimeCompact(latestEvent.occurred_at),
    ]
      .filter(Boolean)
      .join(" · ");
    return {
      id: "active-task",
      label: "Active work",
      value: "Task in progress",
      detail: detailParts,
      tone: "info",
    };
  }
  if (unread > 0) {
    return {
      id: "unread-work",
      label: "Active work",
      value: `${unread} unread update${unread === 1 ? "" : "s"}`,
      detail: latestUnreadAt ? `${formatRelativeTimeCompact(latestUnreadAt)} newest` : undefined,
      tone: "info",
    };
  }
  if (workflowStatus && !workflowStatus.has_active_work) {
    return {
      id: "active-work",
      label: "Active work",
      value: "Monitoring",
      detail: workflowStatus.detail ?? "No pending tasks or escalations",
    };
  }
  return {
    id: "active-work",
    label: "Active work",
    value: "All caught up",
    detail: "No pending tasks or unread updates",
  };
};

const buildInsightCards = (
  summary: PatientTimelineWorklistSummaryItem | null,
  evidence: PatientEscalationEvidence | null,
  taskSummary: PatientInterventionTaskSummary | null,
  workflowStatus: PatientWorkflowStatusSummary | null,
  queueViewName?: string,
  queueFilterSummary?: string | null,
  hasQueueReturnContext?: boolean,
  latestEvent: PatientTimelineItem | null,
  activeEscalationStatus?: EscalationStatus | null,
): InsightCard[] => {
  const fallbackEscalationInsight = buildEscalationInsight(
    summary,
    evidence,
    activeEscalationStatus,
  );
  const workflowInsight =
    workflowStatus !== null
      ? {
          id: "workflow-posture",
          label: "Workflow posture",
          value: workflowStatus.label,
          detail:
            workflowStatus.detail ??
            describeWorkflowDriver(workflowStatus.primary_driver) ??
            fallbackEscalationInsight?.detail ??
            undefined,
          tone: workflowSeverityToTone(workflowStatus.severity) ?? fallbackEscalationInsight?.tone,
        }
      : fallbackEscalationInsight;

  const cards = [
    buildQueueInsight(queueViewName, queueFilterSummary, hasQueueReturnContext),
    workflowInsight,
    buildWorkInsight(summary, taskSummary, latestEvent, workflowStatus),
  ].filter((card): card is InsightCard => Boolean(card));
  return cards;
};

export default function PatientWorkflowHeader({
  patientName,
  patientId,
  summary,
  evidence,
  taskSummary: explicitTaskSummary,
  workflowStatus: explicitWorkflowStatus,
  queueViewName,
  queueFilterSummary,
  hasQueueReturnContext,
  latestEvent,
  activeEscalationStatus,
}: Props) {
  const resolvedTaskSummary = explicitTaskSummary ?? summary?.task_summary ?? null;
  const resolvedWorkflowStatus = explicitWorkflowStatus ?? summary?.workflow_status ?? null;
  const subtitle = buildSubtitle(summary, evidence, resolvedTaskSummary, resolvedWorkflowStatus);
  const metadata = buildMetadata(patientId, summary, resolvedTaskSummary);
  const chips = buildChips(summary, evidence, resolvedTaskSummary, resolvedWorkflowStatus);
  const insightCards = buildInsightCards(
    summary,
    evidence,
    resolvedTaskSummary,
    resolvedWorkflowStatus,
    queueViewName,
    queueFilterSummary,
    hasQueueReturnContext,
    latestEvent,
    activeEscalationStatus,
  );

  return (
    <section className="page-header patient-workflow-header">
      <div className="patient-workflow-header-main">
        <p className="eyebrow">Patient timeline</p>
        <h1>{patientName}</h1>
        <p className="patient-workflow-header-subtitle">{subtitle}</p>
      </div>
      {insightCards.length ? (
        <div className="patient-workflow-insights">
          {insightCards.map((card) => (
            <div
              key={card.id}
              className={`patient-workflow-insight${
                card.tone ? ` patient-workflow-insight--${card.tone}` : ""
              }`}
            >
              <p className="patient-workflow-insight-label">{card.label}</p>
              <p className="patient-workflow-insight-value">{card.value}</p>
              {card.detail ? (
                <p className="patient-workflow-insight-detail">{card.detail}</p>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
      {metadata.length ? (
        <dl className="patient-workflow-meta">
          {metadata.map((item) => (
            <div className="patient-workflow-meta-item" key={item.id}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {chips.length ? (
        <div className="patient-workflow-cues">
          {chips.map((chip) => (
            <div
              key={chip.id}
              className={`patient-workflow-chip${
                chip.tone ? ` patient-workflow-chip--${chip.tone}` : ""
              }`}
            >
              <span className="patient-workflow-chip-label">{chip.label}</span>
              <span className="patient-workflow-chip-value">{chip.value}</span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
