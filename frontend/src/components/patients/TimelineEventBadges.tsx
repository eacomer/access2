import STATUS_LABELS from "../../lib/statusLabels";
import type { PatientTimelineItem } from "../../types/patient";

type Badge = {
  id: string;
  label: string;
  variant?: string;
};

type Props = {
  event: PatientTimelineItem;
};

const OPEN_WORK_STATUSES = new Set(["open", "in_progress", "pending", "at_risk", "overdue"]);

const humanize = (value?: string | null): string | null => {
  if (!value) {
    return null;
  }
  return value
    .split(/[_:-]/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
};

const buildBadges = (event: PatientTimelineItem): Badge[] => {
  const badges: Badge[] = [];

  if (event.related_escalation_id) {
    badges.push({
      id: `${event.event_id}-escalation`,
      label: STATUS_LABELS.linkedEscalation,
      variant: "badge--info",
    });
  }

  if (event.related_task_id) {
    badges.push({
      id: `${event.event_id}-task`,
      label: STATUS_LABELS.linkedTask,
      variant: "badge--warning",
    });
  }

  if (event.related_outcome_id) {
    badges.push({
      id: `${event.event_id}-outcome`,
      label: STATUS_LABELS.linkedOutcome,
      variant: "badge--positive",
    });
  }

  if (event.event_type === "care_update_logged") {
    badges.push({
      id: `${event.event_id}-care-update`,
      label: STATUS_LABELS.careUpdate,
      variant: "badge--info",
    });
  }

  if (event.event_type.startsWith("intervention_task")) {
    if (event.event_type.includes("outcome")) {
      badges.push({
        id: `${event.event_id}-task-outcome`,
        label: STATUS_LABELS.taskOutcome,
        variant: "badge--positive",
      });
    } else if (event.event_type.includes("overdue")) {
      badges.push({
        id: `${event.event_id}-task-overdue`,
        label: STATUS_LABELS.taskOverdue,
        variant: "badge--critical",
      });
    } else if (event.event_type.includes("due_upcoming")) {
      badges.push({
        id: `${event.event_id}-task-upcoming`,
        label: STATUS_LABELS.taskDueSoon,
        variant: "badge--warning",
      });
    } else {
      badges.push({
        id: `${event.event_id}-task-event`,
        label: STATUS_LABELS.taskActivity,
        variant: "badge--info",
      });
    }
  }

  if (event.event_type.startsWith("escalation_")) {
    if (event.event_type.includes("overdue")) {
      badges.push({
        id: `${event.event_id}-escalation-overdue`,
        label: STATUS_LABELS.slaOverdue,
        variant: "badge--critical",
      });
    } else if (event.event_type.includes("sla_at_risk")) {
      badges.push({
        id: `${event.event_id}-escalation-risk`,
        label: STATUS_LABELS.slaAtRisk,
        variant: "badge--warning",
      });
    } else {
      badges.push({
        id: `${event.event_id}-escalation-event`,
        label: STATUS_LABELS.escalationUpdate,
        variant: "badge--info",
      });
    }
  }

  if (event.status && OPEN_WORK_STATUSES.has(event.status)) {
    const statusLabel = humanize(event.status) ?? STATUS_LABELS.openWork;
    badges.push({
      id: `${event.event_id}-status`,
      label: statusLabel,
      variant: "badge--info",
    });
  }

  return badges;
};

export default function TimelineEventBadges({ event }: Props) {
  const badges = buildBadges(event);
  if (!badges.length) {
    return null;
  }

  return (
    <div className="timeline-badges">
      {badges.map((badge) => (
        <span key={badge.id} className={`badge timeline-badge ${badge.variant ?? ""}`}>
          {badge.label}
        </span>
      ))}
    </div>
  );
}
