import Link from "next/link";

import {
  formatDateTime,
  formatDueDate,
  formatEventType,
  formatPriority,
  formatRelativeTimeCompact,
  pluralize,
} from "../../lib/format";
import STATUS_LABELS from "../../lib/statusLabels";
import {
  describeWorkflowDriver,
  workflowSeverityToBadgeVariant,
  workflowSeverityToTone,
} from "../../lib/workflowStatus";
import type { PatientInterventionTaskSummary, PatientTimelineWorklistSummaryItem } from "../../types/patient";

type Props = {
  summary: PatientTimelineWorklistSummaryItem;
  queueQueryString?: string | null;
};

type EmphasisTone = "info" | "warning" | "alert";

const humanizeTaskStatus = (value?: string | null) => {
  if (!value) {
    return null;
  }
  return value
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
};

const getBadge = (
  summary: PatientTimelineWorklistSummaryItem,
  taskSummary: PatientInterventionTaskSummary | null,
) => {
  const workflowStatus = summary.workflow_status ?? null;
  if (workflowStatus) {
    return {
      label: workflowStatus.label,
      variant: workflowSeverityToBadgeVariant(workflowStatus.severity),
    };
  }
  if (taskSummary?.overdue_task_count && taskSummary.overdue_task_count > 0) {
    return { label: `${taskSummary.overdue_task_count} overdue tasks`, variant: "badge--critical" };
  }
  if (taskSummary?.open_task_count && taskSummary.open_task_count > 0) {
    return { label: `${taskSummary.open_task_count} open tasks`, variant: "badge--info" };
  }
  if (summary.overdue_escalation_count > 0) {
    return { label: `${summary.overdue_escalation_count} overdue`, variant: "badge--critical" };
  }
  if (summary.at_risk_escalation_count > 0) {
    return { label: `${summary.at_risk_escalation_count} at risk`, variant: "badge--warning" };
  }
  if (summary.open_escalation_count > 0) {
    return { label: `${summary.open_escalation_count} open`, variant: "badge--info" };
  }
  return { label: "No escalations", variant: "badge--positive" };
};

const buildDetailLink = (
  summary: PatientTimelineWorklistSummaryItem,
  queueQueryString: string | null | undefined,
  taskSummary: PatientInterventionTaskSummary | null,
) => {
  const params = new URLSearchParams();
  const chips: string[] = [];

  if (summary.latest_open_escalation_id) {
    params.set("related_escalation_id", summary.latest_open_escalation_id);
    chips.push(STATUS_LABELS.activeEscalation);
  }

  if (taskSummary?.latest_active_task_id) {
    params.set("related_task_id", taskSummary.latest_active_task_id);
    chips.push("Active task context");
  }

  const hasOpenWork =
    summary.open_escalation_count > 0 ||
    summary.overdue_escalation_count > 0 ||
    summary.at_risk_escalation_count > 0;

  if (hasOpenWork) {
    params.set("include_only_open_work", "1");
    chips.push(`${STATUS_LABELS.openWork} filter`);
  }

  if (queueQueryString && queueQueryString.length > 0) {
    params.set("queue_query", queueQueryString);
  }

  const hrefParams = params.toString();
  const href = hrefParams
    ? `/patients/${summary.patient_id}?${hrefParams}`
    : `/patients/${summary.patient_id}`;

  return {
    href,
    chips,
    helper: hrefParams
      ? "View timeline evidence with context"
      : "View full patient timeline",
  };
};

type AttentionSummary = {
  primary: string;
  detail: string;
  tone?: EmphasisTone;
};

const buildAttentionDetailParts = (
  summary: PatientTimelineWorklistSummaryItem,
  taskSummary: PatientInterventionTaskSummary | null,
) => {
  const detailParts: string[] = [];
  if (taskSummary?.latest_active_task_title) {
    detailParts.push(taskSummary.latest_active_task_title);
  } else if (summary.latest_event_title) {
    detailParts.push(summary.latest_event_title);
  } else if (summary.latest_event_type) {
    detailParts.push(formatEventType(summary.latest_event_type));
  }
  const taskTimestamp =
    taskSummary?.latest_active_task_due_at ?? taskSummary?.latest_active_task_created_at ?? null;
  if (taskTimestamp) {
    detailParts.push(`${formatRelativeTimeCompact(taskTimestamp)} · ${formatDateTime(taskTimestamp)}`);
  } else if (summary.latest_event_occurred_at) {
    const relative = formatRelativeTimeCompact(summary.latest_event_occurred_at);
    detailParts.push(`${relative} · ${formatDateTime(summary.latest_event_occurred_at)}`);
  }
  return detailParts;
};

const buildAttentionSummary = (summary: PatientTimelineWorklistSummaryItem): AttentionSummary => {
  const taskSummary = summary.task_summary ?? null;
  const workflowStatus = summary.workflow_status ?? null;
  if (workflowStatus) {
    const tone = workflowSeverityToTone(workflowStatus.severity);
    const detailParts: string[] = [];
    if (workflowStatus.detail) {
      detailParts.push(workflowStatus.detail);
    }
    if (!workflowStatus.detail) {
      detailParts.push(...buildAttentionDetailParts(summary, taskSummary));
    }
    const driver = describeWorkflowDriver(workflowStatus.primary_driver);
    if (driver && !detailParts.includes(driver)) {
      detailParts.push(driver);
    }
    return {
      primary: workflowStatus.label,
      detail: detailParts.join(" • "),
      tone,
    };
  }
  const {
    overdue_escalation_count,
    at_risk_escalation_count,
    open_escalation_count,
    has_unread_events,
    unread_count,
    highest_escalation_priority,
  } = summary;

  let primary = "Review patient timeline";
  let tone: EmphasisTone | undefined;

  if (taskSummary) {
    if (taskSummary.overdue_task_count > 0) {
      primary = pluralize(taskSummary.overdue_task_count, "task overdue", "tasks overdue");
      tone = "alert";
    } else if (taskSummary.open_task_count > 0) {
      primary =
        taskSummary.in_progress_task_count > 0
          ? pluralize(taskSummary.in_progress_task_count, "task in progress", "tasks in progress")
          : pluralize(taskSummary.open_task_count, "open task");
      tone = "info";
    } else {
      primary = "No active tasks";
    }
  }

  if (overdue_escalation_count > 0) {
    primary =
      overdue_escalation_count === 1
        ? "Escalation SLA is overdue"
        : `${overdue_escalation_count} escalations overdue`;
    tone = "alert";
  } else if (at_risk_escalation_count > 0) {
    primary =
      at_risk_escalation_count === 1
        ? "Escalation SLA at risk"
        : `${at_risk_escalation_count} escalations at risk`;
    tone = "warning";
  } else if (open_escalation_count > 0) {
    primary =
      open_escalation_count === 1
        ? "Active escalation requires attention"
        : `${open_escalation_count} open escalations`;
    tone = "info";
  } else if (has_unread_events && unread_count > 0) {
    primary = `${unread_count} new timeline ${unread_count === 1 ? "event" : "events"}`;
    tone = "info";
  }

  if (highest_escalation_priority) {
    primary = `${primary} · ${formatPriority(highest_escalation_priority)}`;
  }

  return {
    primary,
    detail: buildAttentionDetailParts(summary, taskSummary).join(" • "),
    tone,
  };
};

type AttentionChip = {
  id: string;
  label: string;
  value: string;
  tone?: EmphasisTone;
};

type ActionCue = {
  label: string;
  helper: string;
  tone?: EmphasisTone;
};

const buildActionCue = (summary: PatientTimelineWorklistSummaryItem): ActionCue | null => {
  const workflowStatus = summary.workflow_status ?? null;
  if (workflowStatus) {
    const tone = workflowSeverityToTone(workflowStatus.severity);
    let label = "Active workflow";
    let helper = workflowStatus.detail ?? describeWorkflowDriver(workflowStatus.primary_driver) ?? "Workflow posture context";
    if (!workflowStatus.has_active_work) {
      label = "Monitoring only";
      helper = workflowStatus.detail ?? "No active escalations or tasks";
    } else if (workflowStatus.primary_driver === "task") {
      if (workflowStatus.severity === "overdue") {
        label = "Resolve overdue tasks";
      } else if (workflowStatus.severity === "urgent") {
        label = "Monitor task urgency";
      } else {
        label = "Active tasks in progress";
      }
      helper = workflowStatus.detail ?? "Task posture requires follow-up";
    } else if (workflowStatus.primary_driver === "escalation") {
      if (workflowStatus.severity === "overdue") {
        label = "Immediate escalation follow-up";
      } else if (workflowStatus.severity === "urgent") {
        label = "Monitor SLA risk";
      } else {
        label = "Escalation work active";
      }
      helper = workflowStatus.detail ?? "Escalation posture requires review";
    }
    return {
      label,
      helper,
      tone,
    };
  }
  const taskSummary = summary.task_summary ?? null;
  if (taskSummary?.overdue_task_count && taskSummary.overdue_task_count > 0) {
    return {
      label: "Resolve overdue tasks",
      helper: "Task summary shows overdue workflow items",
      tone: "alert",
    };
  }
  if (taskSummary?.in_progress_task_count && taskSummary.in_progress_task_count > 0) {
    return {
      label: "Active tasks in progress",
      helper: "Monitor intervention tasks to completion",
      tone: "info",
    };
  }
  if (taskSummary?.open_task_count && taskSummary.open_task_count > 0) {
    return {
      label: "Open tasks",
      helper: "Tasks pending review or assignment",
      tone: "info",
    };
  }
  if (summary.overdue_escalation_count > 0) {
    return {
      label: "Immediate follow-up",
      helper: "Resolve overdue escalations first",
      tone: "alert",
    };
  }
  if (summary.at_risk_escalation_count > 0) {
    return {
      label: "Monitor SLA risk",
      helper: "Escalations are approaching SLA breach",
      tone: "warning",
    };
  }
  if (summary.open_escalation_count > 0) {
    return {
      label: "Active work open",
      helper: "Queue includes open escalations",
      tone: "info",
    };
  }
  if (summary.has_unread_events && summary.unread_count > 0) {
    return {
      label: "Review new activity",
      helper: "Unread timeline updates available",
      tone: "info",
    };
  }
  return {
    label: "No pending action",
    helper: "Queue context preserved for reference",
  };
};

const buildAttentionChips = (summary: PatientTimelineWorklistSummaryItem): AttentionChip[] => {
  const chips: AttentionChip[] = [];
  const taskSummary = summary.task_summary ?? null;
  const workflowStatus = summary.workflow_status ?? null;

  if (workflowStatus) {
    const driverLabel = describeWorkflowDriver(workflowStatus.primary_driver);
    chips.push({
      id: "workflow-driver",
      label: "Workflow posture",
      value: workflowStatus.label,
      tone: workflowStatus.has_active_work ? workflowSeverityToTone(workflowStatus.severity) : undefined,
    });
    if (driverLabel) {
      chips.push({
        id: "workflow-driver-detail",
        label: "Driver",
        value: driverLabel,
      });
    }
  }

  if (taskSummary?.overdue_task_count && taskSummary.overdue_task_count > 0) {
    chips.push({
      id: "tasks-overdue",
      label: "Tasks overdue",
      value: String(taskSummary.overdue_task_count),
      tone: "alert",
    });
  }
  if (taskSummary?.in_progress_task_count && taskSummary.in_progress_task_count > 0) {
    chips.push({
      id: "tasks-progress",
      label: "In progress",
      value: String(taskSummary.in_progress_task_count),
      tone: "info",
    });
  }
  if (taskSummary?.open_task_count && taskSummary.open_task_count > 0) {
    chips.push({
      id: "tasks-open",
      label: "Open tasks",
      value: String(taskSummary.open_task_count),
    });
  }

  if (summary.has_unread_events && summary.unread_count > 0) {
    chips.push({
      id: "unread",
      label: STATUS_LABELS.unreadActivity,
      value: String(summary.unread_count),
      tone: "info",
    });
  }

  if (summary.highest_escalation_priority) {
    chips.push({
      id: "priority",
      label: "Priority",
      value: formatPriority(summary.highest_escalation_priority),
    });
  }

  if (summary.next_escalation_sla_due_at) {
    chips.push({
      id: "sla",
      label: STATUS_LABELS.nextSlaDue,
      value: formatDueDate(summary.next_escalation_sla_due_at),
      tone: summary.overdue_escalation_count > 0 ? "alert" : undefined,
    });
  }

  if (summary.latest_event_type) {
    chips.push({
      id: "latest-type",
      label: STATUS_LABELS.latestEvent,
      value: formatEventType(summary.latest_event_type),
    });
  }

  return chips.slice(0, 4);
};

type FreshnessTone = "fresh" | "recent" | "stale";

type RecencyContext = {
  timestamp: string;
  relative?: string;
  tone?: FreshnessTone;
  chips: AttentionChip[];
};

const getFreshnessTone = (occurredAt?: string | null): FreshnessTone | undefined => {
  if (!occurredAt) {
    return undefined;
  }
  const date = new Date(occurredAt);
  if (Number.isNaN(date.getTime())) {
    return undefined;
  }
  const diffHours = (Date.now() - date.getTime()) / (1000 * 60 * 60);
  if (diffHours <= 6) {
    return "fresh";
  }
  if (diffHours <= 24) {
    return "recent";
  }
  return "stale";
};

const buildRecencyContext = (summary: PatientTimelineWorklistSummaryItem): RecencyContext | null => {
  const taskSummary = summary.task_summary ?? null;
  const taskTimestamp =
    taskSummary?.latest_active_task_due_at ?? taskSummary?.latest_active_task_created_at ?? null;
  const { latest_event_occurred_at, latest_event_type, has_unread_events, unread_count } = summary;
  const effectiveTimestamp = taskTimestamp ?? latest_event_occurred_at;
  if (!effectiveTimestamp && !latest_event_type && !(has_unread_events && unread_count > 0)) {
    return null;
  }

  const timestamp = effectiveTimestamp
    ? formatDateTime(effectiveTimestamp)
    : "No recent updates recorded";
  const relative =
    effectiveTimestamp && !Number.isNaN(new Date(effectiveTimestamp).getTime())
      ? formatRelativeTimeCompact(effectiveTimestamp)
      : undefined;
  const tone = getFreshnessTone(effectiveTimestamp);

  const chips: AttentionChip[] = [];
  if (taskSummary?.latest_active_task_title) {
    chips.push({
      id: "latest-task",
      label: "Active task",
      value: taskSummary.latest_active_task_title,
    });
  } else if (latest_event_type) {
    chips.push({
      id: "latest-event-type",
      label: STATUS_LABELS.latestEvent,
      value: formatEventType(latest_event_type),
    });
  }
  if (has_unread_events && unread_count > 0) {
    chips.push({
      id: "recency-unread",
      label: STATUS_LABELS.unreadActivity,
      value: `${unread_count}`,
      tone: "info",
    });
  }

  return { timestamp, relative, tone, chips };
};

export default function WorklistSummaryCard({ summary, queueQueryString }: Props) {
  const taskSummary = summary.task_summary ?? null;
  const badge = getBadge(summary, taskSummary);
  const detailLink = buildDetailLink(summary, queueQueryString, taskSummary);
  const attention = buildAttentionSummary(summary);
  const attentionChips = buildAttentionChips(summary);
  const recency = buildRecencyContext(summary);
  const actionCue = buildActionCue(summary);
  const compactAttentionReason = summary.attention_reason ?? attention.primary;
  const compactNextStep = summary.next_step ?? actionCue?.label ?? "Standing by";
  const compactNextStepReason = summary.next_step_reason ?? actionCue?.helper ?? null;
  const compactCareGap = summary.care_gap_label ?? null;
  const compactBlockingIssue = summary.blocking_issue_label ?? null;
  const compactResolutionTarget = summary.resolution_target_label ?? null;
  const compactClosureReadiness = summary.closure_readiness_label ?? null;
  const compactResolutionConfidence = summary.resolution_confidence_label ?? null;
  const compactRecommendedTimeframe = summary.recommended_timeframe ?? null;
  const compactWorkflowAge = summary.workflow_age_label ?? null;
  const compactRecentChange = summary.recent_change_label ?? null;
  const compactStaleness = summary.staleness_indicator ?? null;
  const compactPriorityBand = summary.priority_band ?? null;
  const compactPriorityReason = summary.priority_reason ?? null;
  const compactStatusSnapshot = summary.status_snapshot ?? null;
  const latestActivityTimestamp =
    taskSummary?.latest_active_task_created_at ?? summary.latest_event_occurred_at ?? null;
  const latestEventSummary = latestActivityTimestamp
    ? `${formatRelativeTimeCompact(latestActivityTimestamp)} · ${formatDateTime(latestActivityTimestamp)}`
    : "n/a";
  const latestEventHeadline =
    taskSummary?.latest_active_task_title ??
    (taskSummary?.latest_active_task_status
      ? humanizeTaskStatus(taskSummary.latest_active_task_status)
      : null) ??
    summary.latest_event_title ??
    (summary.latest_event_type ? formatEventType(summary.latest_event_type) : "No recent timeline activity");
  const attentionDetail = attention.detail.length ? attention.detail : "No additional evidence captured.";

  const workflowBadges: Array<{ id: string; content: string; variant?: string }> = [];
  if (taskSummary?.open_task_count) {
    workflowBadges.push({
      id: "workflow-tasks",
      content: `${taskSummary.open_task_count} open task${taskSummary.open_task_count === 1 ? "" : "s"}`,
      variant: "badge--info",
    });
  }
  if (taskSummary?.latest_active_task_status) {
    workflowBadges.push({
      id: "workflow-task-status",
      content: humanizeTaskStatus(taskSummary.latest_active_task_status) ?? "Task active",
    });
  }
  if (summary.highest_escalation_priority) {
    workflowBadges.push({
      id: "workflow-priority",
      content: `Priority ${formatPriority(summary.highest_escalation_priority)}`,
    });
  }
  if (summary.next_escalation_sla_due_at) {
    workflowBadges.push({
      id: "workflow-sla",
      content: `Next SLA ${formatDueDate(summary.next_escalation_sla_due_at)}`,
      variant: "badge--info",
    });
  }
  if (summary.has_unread_events && summary.unread_count > 0) {
    workflowBadges.push({
      id: "workflow-unread",
      content: `${summary.unread_count} ${STATUS_LABELS.unreadActivity.toLowerCase()}`,
      variant: "badge--info",
    });
  }

  const metrics = taskSummary
    ? [
        { id: "tasks-open", label: "Open tasks", value: taskSummary.open_task_count },
        { id: "tasks-progress", label: "In progress", value: taskSummary.in_progress_task_count },
        { id: "tasks-overdue", label: "Overdue", value: taskSummary.overdue_task_count },
      ]
    : [
        { id: "esc-open", label: "Open", value: summary.open_escalation_count },
        { id: "esc-overdue", label: "Overdue", value: summary.overdue_escalation_count },
        { id: "esc-at-risk", label: "At risk", value: summary.at_risk_escalation_count },
      ];

  return (
    <Link
      href={detailLink.href}
      className="card card-link worklist-card worklist-card--triage"
      aria-label={`${detailLink.helper} for ${summary.patient_display_name}`}
    >
      <header className="worklist-card-headline">
        <div className="worklist-card-identity">
          <p className="eyebrow">Patient queue</p>
          <p className="card-title">{summary.patient_display_name}</p>
          <p className="card-id">{summary.patient_id}</p>
        </div>
        <div className="worklist-card-status">
          <span className={`badge ${badge.variant}`}>{badge.label}</span>
          {workflowBadges.length ? (
            <div className="worklist-headline-cues">
              {summary.attention_reason ? (
                <span className="badge badge--info">{summary.attention_reason}</span>
              ) : null}
              {workflowBadges.slice(0, 2).map((item) => (
                <span key={item.id} className={`badge${item.variant ? ` ${item.variant}` : ""}`}>
                  {item.content}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </header>

      <div className="worklist-card-topline" aria-label="Queue scan line">
        <div className="worklist-topline-item">
          <span className="worklist-topline-label">Reason</span>
          <span
            className={`worklist-topline-value${
              attention.tone ? ` worklist-topline-value--${attention.tone}` : ""
            }`}
          >
            {compactAttentionReason}
          </span>
        </div>
        <div className="worklist-topline-item">
          <span className="worklist-topline-label">Action</span>
          <span
            className={`worklist-action-pill${
              actionCue?.tone ? ` worklist-action-pill--${actionCue.tone}` : ""
            }`}
          >
            {compactNextStep}
          </span>
          {compactNextStepReason ? (
            <span className="worklist-topline-helper">{compactNextStepReason}</span>
          ) : null}
          {compactStatusSnapshot ? (
            <span className="worklist-topline-helper">{compactStatusSnapshot}</span>
          ) : null}
          {compactCareGap ? (
            <span className="worklist-topline-helper">Care gap: {compactCareGap}</span>
          ) : null}
          {compactBlockingIssue ? (
            <span className="worklist-topline-helper">Blocker: {compactBlockingIssue}</span>
          ) : null}
          {compactResolutionTarget ? (
            <span className="worklist-topline-helper">Done: {compactResolutionTarget}</span>
          ) : null}
          {compactClosureReadiness ? (
            <span className="worklist-topline-helper">Closure: {compactClosureReadiness}</span>
          ) : null}
          {compactResolutionConfidence ? (
            <span className="worklist-topline-helper">Confidence: {compactResolutionConfidence}</span>
          ) : null}
          {compactRecommendedTimeframe ? (
            <span className="worklist-topline-helper">Timeframe: {compactRecommendedTimeframe}</span>
          ) : null}
          {compactWorkflowAge ? (
            <span className="worklist-topline-helper">Age: {compactWorkflowAge}</span>
          ) : null}
          {compactRecentChange ? (
            <span className="worklist-topline-helper">{compactRecentChange}</span>
          ) : null}
          {compactStaleness ? (
            <span className="worklist-topline-helper">Staleness: {compactStaleness}</span>
          ) : null}
          {compactPriorityBand ? (
            <span className="worklist-topline-helper">Priority: {compactPriorityBand}</span>
          ) : null}
          {compactPriorityReason ? (
            <span className="worklist-topline-helper">{compactPriorityReason}</span>
          ) : null}
        </div>
        <div className="worklist-topline-item">
          <span className="worklist-topline-label">Latest</span>
          <span
            className={`worklist-topline-value${
              recency?.tone ? ` worklist-topline-value--freshness-${recency.tone}` : ""
            }`}
          >
            {recency?.relative ?? "No updates recorded"}
          </span>
          <span className="worklist-topline-helper">
            {recency?.timestamp ?? "No timeline evidence yet"}
          </span>
        </div>
      </div>

      <div className="worklist-triage-grid">
        <div className="worklist-triage-block">
          <p className="worklist-triage-label">Queue detail</p>
          <p className="worklist-triage-value">{attentionDetail}</p>
          {attentionChips.length ? (
            <div className="worklist-attention-chips">
              {attentionChips.map((chip) => (
                <div
                  key={chip.id}
                  className={`worklist-attention-chip${
                    chip.tone ? ` worklist-attention-chip--${chip.tone}` : ""
                  }`}
                >
                  <span className="worklist-attention-chip-label">{chip.label}</span>
                  <span className="worklist-attention-chip-value">{chip.value}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="worklist-triage-detail">No supporting evidence captured.</p>
          )}
        </div>

        <div className="worklist-triage-block">
          <p className="worklist-triage-label">Latest activity</p>
          <p className="worklist-activity-main">{latestEventHeadline}</p>
          {recency ? (
            <>
              <p className="worklist-activity-meta">
                {recency.relative ? `${recency.relative} · ` : ""}
                {recency.timestamp}
              </p>
              {recency.chips.length ? (
                <div className="worklist-attention-chips worklist-recency-chips">
                  {recency.chips.map((chip) => (
                    <div
                      key={chip.id}
                      className={`worklist-attention-chip${
                        chip.tone ? ` worklist-attention-chip--${chip.tone}` : ""
                      }`}
                    >
                      <span className="worklist-attention-chip-label">{chip.label}</span>
                      <span className="worklist-attention-chip-value">{chip.value}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </>
          ) : (
            <p className="worklist-triage-detail">No timeline evidence recorded.</p>
          )}
          <p className="worklist-card-note">{`Latest event: ${latestEventSummary}`}</p>
        </div>

        <div className="worklist-triage-block worklist-triage-block--metrics">
          <p className="worklist-triage-label">
            {taskSummary ? "Task pulse" : "Escalation pulse"}
          </p>
          <div className="worklist-metric-row">
            {metrics.map((metric) => (
              <div className="worklist-metric" key={metric.id}>
                <span className="worklist-metric-value">{metric.value}</span>
                <span className="worklist-metric-label">{metric.label}</span>
              </div>
            ))}
          </div>
          {workflowBadges.length ? (
            <div className="worklist-metric-badges">
              {workflowBadges.slice(0, 2).map((item) => (
                <span key={item.id} className={`badge${item.variant ? ` ${item.variant}` : ""}`}>
                  {item.content}
                </span>
              ))}
            </div>
          ) : (
            <p className="worklist-triage-detail">
              {taskSummary ? "No additional task cues surfaced." : "No workflow cues surfaced."}
            </p>
          )}
        </div>
      </div>

      <section className="worklist-card-section worklist-card-action">
        <div className="worklist-card-action-main">
          <div>
            <p className="worklist-context-label">Drill-through</p>
            <p className="worklist-card-action-text">{detailLink.helper}</p>
            <p className="worklist-card-note">
              {actionCue?.helper ?? "Review patient timeline context"}
            </p>
          </div>
          <span className="worklist-card-action-arrow" aria-hidden="true">
            →
          </span>
        </div>
        {detailLink.chips.length > 0 ? (
          <div className="filter-chip-group">
            {detailLink.chips.map((chip) => (
              <span key={chip} className="badge filter-chip">
                {chip}
              </span>
            ))}
          </div>
        ) : null}
      </section>
    </Link>
  );
}
