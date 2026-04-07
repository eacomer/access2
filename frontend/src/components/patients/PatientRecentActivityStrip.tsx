import { formatDateTime, formatEventType, formatRelativeTimeCompact } from "../../lib/format";
import STATUS_LABELS from "../../lib/statusLabels";
import type {
  PatientTimelineItem,
  PatientTimelineWorklistSummaryItem,
} from "../../types/patient";

type Props = {
  latestEvent: PatientTimelineItem | null;
  summary: PatientTimelineWorklistSummaryItem | null;
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

const buildEscalationCue = (summary: PatientTimelineWorklistSummaryItem | null): Cue | null => {
  if (!summary) {
    return null;
  }
  if (summary.overdue_escalation_count > 0) {
    return {
      id: "escalation-overdue",
      label: "Escalations",
      value: `${summary.overdue_escalation_count} overdue`,
      tone: "alert",
      detail: summary.next_escalation_sla_due_at
        ? `Next SLA ${formatRelativeTimeCompact(summary.next_escalation_sla_due_at)}`
        : undefined,
    };
  }
  if (summary.at_risk_escalation_count > 0) {
    return {
      id: "escalation-at-risk",
      label: "Escalations",
      value: `${summary.at_risk_escalation_count} at risk`,
      tone: "warning",
      detail: summary.next_escalation_sla_due_at
        ? `Next SLA ${formatRelativeTimeCompact(summary.next_escalation_sla_due_at)}`
        : undefined,
    };
  }
  if (summary.open_escalation_count > 0) {
    return {
      id: "escalation-open",
      label: "Escalations",
      value: `${summary.open_escalation_count} active`,
      tone: "info",
    };
  }
  return null;
};

export default function PatientRecentActivityStrip({ latestEvent, summary }: Props) {
  const cues: Cue[] = [];
  const lastEventCue = buildLastEventCue(latestEvent, summary);
  if (lastEventCue) {
    cues.push(lastEventCue);
  }
  const unreadCue = buildUnreadCue(summary);
  if (unreadCue) {
    cues.push(unreadCue);
  }
  const escalationCue = buildEscalationCue(summary);
  if (escalationCue) {
    cues.push(escalationCue);
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
