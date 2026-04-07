import Link from "next/link";

import {
  formatDateTime,
  formatDueDate,
  formatEventType,
  formatPriority,
  formatRelativeTimeCompact,
} from "../../lib/format";
import STATUS_LABELS from "../../lib/statusLabels";
import type { PatientTimelineWorklistSummaryItem } from "../../types/patient";

type Props = {
  summary: PatientTimelineWorklistSummaryItem;
  queueQueryString?: string | null;
};

const getBadge = (summary: PatientTimelineWorklistSummaryItem) => {
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
  queueQueryString?: string | null,
) => {
  const params = new URLSearchParams();
  const chips: string[] = [];

  if (summary.latest_open_escalation_id) {
    params.set("related_escalation_id", summary.latest_open_escalation_id);
    chips.push(STATUS_LABELS.activeEscalation);
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

const buildAttentionSummary = (summary: PatientTimelineWorklistSummaryItem) => {
  const {
    overdue_escalation_count,
    at_risk_escalation_count,
    open_escalation_count,
    has_unread_events,
    unread_count,
    highest_escalation_priority,
    latest_event_title,
    latest_event_occurred_at,
    latest_event_type,
  } = summary;

  let primary = "Review patient timeline";

  if (overdue_escalation_count > 0) {
    primary =
      overdue_escalation_count === 1
        ? "Escalation SLA is overdue"
        : `${overdue_escalation_count} escalations overdue`;
  } else if (at_risk_escalation_count > 0) {
    primary =
      at_risk_escalation_count === 1
        ? "Escalation SLA at risk"
        : `${at_risk_escalation_count} escalations at risk`;
  } else if (open_escalation_count > 0) {
    primary =
      open_escalation_count === 1
        ? "Active escalation requires attention"
        : `${open_escalation_count} open escalations`;
  } else if (has_unread_events && unread_count > 0) {
    primary = `${unread_count} new timeline ${unread_count === 1 ? "event" : "events"}`;
  }

  if (highest_escalation_priority) {
    primary = `${primary} · ${formatPriority(highest_escalation_priority)}`;
  }

  const detailParts: string[] = [];
  if (latest_event_title) {
    detailParts.push(latest_event_title);
  } else if (latest_event_type) {
    detailParts.push(formatEventType(latest_event_type));
  }
  if (latest_event_occurred_at) {
    const relative = formatRelativeTimeCompact(latest_event_occurred_at);
    detailParts.push(`${relative} · ${formatDateTime(latest_event_occurred_at)}`);
  }

  return {
    primary,
    detail: detailParts.join(" • "),
  };
};

type AttentionChip = {
  id: string;
  label: string;
  value: string;
  tone?: "info" | "warning" | "alert";
};

const buildAttentionChips = (summary: PatientTimelineWorklistSummaryItem): AttentionChip[] => {
  const chips: AttentionChip[] = [];

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
  const { latest_event_occurred_at, latest_event_type, has_unread_events, unread_count } = summary;
  if (!latest_event_occurred_at && !latest_event_type && !(has_unread_events && unread_count > 0)) {
    return null;
  }

  const timestamp = latest_event_occurred_at
    ? formatDateTime(latest_event_occurred_at)
    : "No recent updates recorded";
  const relative =
    latest_event_occurred_at && !Number.isNaN(new Date(latest_event_occurred_at).getTime())
      ? formatRelativeTimeCompact(latest_event_occurred_at)
      : undefined;
  const tone = getFreshnessTone(latest_event_occurred_at);

  const chips: AttentionChip[] = [];
  if (latest_event_type) {
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
  const badge = getBadge(summary);
  const detailLink = buildDetailLink(summary, queueQueryString);
  const attention = buildAttentionSummary(summary);
  const attentionChips = buildAttentionChips(summary);
  const recency = buildRecencyContext(summary);
  const latestEventSummary = summary.latest_event_occurred_at
    ? `${formatRelativeTimeCompact(summary.latest_event_occurred_at)} · ${formatDateTime(summary.latest_event_occurred_at)}`
    : "n/a";

  const workflowBadges: Array<{ id: string; content: string; variant?: string }> = [];
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

  return (
    <Link
      href={detailLink.href}
      className="card card-link"
      aria-label={`${detailLink.helper} for ${summary.patient_display_name}`}
    >
      <header className="worklist-card-head">
        <div>
          <p className="eyebrow">Patient</p>
          <p className="card-title">{summary.patient_display_name}</p>
          <p className="card-id">{summary.patient_id}</p>
        </div>
        <span className={`badge ${badge.variant}`}>{badge.label}</span>
      </header>

      <section className="worklist-card-section">
        <p className="worklist-context-label">Attention focus</p>
        <p className="worklist-card-primary">{attention.primary}</p>
        {attention.detail ? (
          <p className="worklist-attention-detail">{attention.detail}</p>
        ) : null}
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
        ) : null}
      </section>

      {recency ? (
        <section className="worklist-card-section">
          <p className="worklist-context-label">Latest activity</p>
          <div className="worklist-recency">
            <div className="worklist-recency-meta">
              <span className="worklist-recency-label">Last update</span>
              <span className="worklist-recency-value">{recency.timestamp}</span>
              {recency.relative ? (
                <span
                  className={`worklist-recency-pill${
                    recency.tone ? ` worklist-recency-pill--${recency.tone}` : ""
                  }`}
                >
                  {recency.relative}
                </span>
              ) : null}
            </div>
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
          </div>
          <p className="worklist-card-note">{`Latest event: ${latestEventSummary}`}</p>
        </section>
      ) : null}

      <section className="worklist-card-section">
        <p className="worklist-context-label">Escalation counts</p>
        <div className="count-row">
          <div className="count-block">
            <span className="count-value">{summary.open_escalation_count}</span>
            <span className="count-label">Open escalations</span>
          </div>
          <div className="count-block">
            <span className="count-value">{summary.overdue_escalation_count}</span>
            <span className="count-label">Overdue</span>
          </div>
          <div className="count-block">
            <span className="count-value">{summary.at_risk_escalation_count}</span>
            <span className="count-label">At risk</span>
          </div>
        </div>
      </section>

      {workflowBadges.length ? (
        <section className="worklist-card-section">
          <p className="worklist-context-label">Workflow cues</p>
          <div className="meta-row">
            {workflowBadges.map((item) => (
              <span key={item.id} className={`badge${item.variant ? ` ${item.variant}` : ""}`}>
                {item.content}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      <section className="worklist-card-section worklist-card-action">
        <div className="worklist-card-action-main">
          <div>
            <p className="worklist-context-label">Drill-through</p>
            <p className="worklist-card-action-text">{detailLink.helper}</p>
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
