import Link from "next/link";

import { formatDateTime, formatDueDate, formatPriority } from "../../lib/format";
import type { PatientTimelineWorklistSummaryItem } from "../../types/patient";

type Props = {
  summary: PatientTimelineWorklistSummaryItem;
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

export default function WorklistSummaryCard({ summary }: Props) {
  const badge = getBadge(summary);

  return (
    <Link href={`/patients/${summary.patient_id}`} className="card card-link">
      <div className="meta-row" style={{ justifyContent: "space-between" }}>
        <div>
          <p className="card-title">{summary.patient_display_name}</p>
          <p className="card-subtitle">
            {summary.latest_event_title ?? "No timeline events yet"}
          </p>
        </div>
        <span className={`badge ${badge.variant}`}>{badge.label}</span>
      </div>
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
      <div className="meta-row">
        {summary.highest_escalation_priority && (
          <span className="badge">{`Priority ${formatPriority(summary.highest_escalation_priority)}`}</span>
        )}
        {summary.next_escalation_sla_due_at && (
          <span className="badge badge--info">
            Next SLA {formatDueDate(summary.next_escalation_sla_due_at)}
          </span>
        )}
      </div>
      <div className="footer-row">
        <span>
          Latest event:{" "}
          {summary.latest_event_occurred_at
            ? formatDateTime(summary.latest_event_occurred_at)
            : "n/a"}
        </span>
        {summary.has_unread_events && (
          <span className="badge badge--info">{`${summary.unread_count} unread`}</span>
        )}
      </div>
    </Link>
  );
}
