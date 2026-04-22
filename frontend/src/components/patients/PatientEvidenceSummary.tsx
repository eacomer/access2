import {
  formatDateTime,
  formatDueDate,
  formatEventType,
  formatPriority,
  pluralize,
} from "../../lib/format";
import type {
  PatientEscalationEvidence,
  PatientTimelineWorklistSummaryItem,
} from "../../types/patient";

type Props = {
  evidence: PatientEscalationEvidence | null;
  summary: PatientTimelineWorklistSummaryItem | null;
};

const getBadge = (
  evidence: PatientEscalationEvidence | null,
  summary: PatientTimelineWorklistSummaryItem | null,
) => {
  const overdue = evidence?.overdue_escalation_count ?? summary?.overdue_escalation_count ?? 0;
  const atRisk = evidence?.at_risk_escalation_count ?? summary?.at_risk_escalation_count ?? 0;
  const open = evidence?.open_escalation_count ?? summary?.open_escalation_count ?? 0;

  if (overdue > 0) {
    return { label: `${pluralize(overdue, "overdue escalation")}`, variant: "badge--critical" };
  }
  if (atRisk > 0) {
    return { label: `${pluralize(atRisk, "at-risk escalation")}`, variant: "badge--warning" };
  }
  if (open > 0) {
    return { label: `${pluralize(open, "open escalation")}`, variant: "badge--info" };
  }
  return { label: "All clear", variant: "badge--positive" };
};

const formatStatus = (
  evidence: PatientEscalationEvidence | null,
  summary: PatientTimelineWorklistSummaryItem | null,
): string => {
  const latestStatus = evidence?.latest_open_escalation_status ?? null;
  if (latestStatus) {
    return latestStatus
      .split("_")
      .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
      .join(" ");
  }
  const hasOpen =
    evidence?.has_open_escalation ||
    (summary?.open_escalation_count ?? 0) > 0 ||
    (summary?.overdue_escalation_count ?? 0) > 0;
  return hasOpen ? "Open escalation" : "No active escalation";
};

export default function PatientEvidenceSummary({ evidence, summary }: Props) {
  const hasEvidence = Boolean(evidence || summary);
  const badge = getBadge(evidence, summary);

  if (!hasEvidence) {
    return (
      <section className="section-card">
        <div className="section-header">
          <div>
            <p className="eyebrow">Operational snapshot</p>
            <h2 className="section-title">Escalation summary</h2>
          </div>
        </div>
        <p className="empty-state">
          Operational evidence is not available for this patient yet. Refresh once timeline events
          start arriving.
        </p>
      </section>
    );
  }

  const priority =
    evidence?.highest_open_escalation_priority ?? summary?.highest_escalation_priority ?? null;
  const slaDue =
    evidence?.next_open_escalation_sla_due_at ?? summary?.next_escalation_sla_due_at ?? null;
  const open = evidence?.open_escalation_count ?? summary?.open_escalation_count ?? 0;
  const overdue =
    evidence?.overdue_escalation_count ?? summary?.overdue_escalation_count ?? 0;
  const atRisk = evidence?.at_risk_escalation_count ?? summary?.at_risk_escalation_count ?? 0;
  const latestOccurredAt =
    evidence?.latest_escalation_event_occurred_at ?? summary?.latest_event_occurred_at ?? null;
  const latestType =
    evidence?.latest_escalation_event_type ?? summary?.latest_event_type ?? null;

  const openWorkLabel =
    open > 0
      ? [
          pluralize(open, "open escalation"),
          overdue > 0 ? pluralize(overdue, "overdue escalation") : null,
          atRisk > 0 ? pluralize(atRisk, "at-risk escalation") : null,
        ]
          .filter(Boolean)
          .join(" · ")
      : "No open escalation work right now";

  const latestUpdateLabel = latestOccurredAt
    ? `${formatDateTime(latestOccurredAt)}${
        latestType ? ` · ${formatEventType(latestType)}` : ""
      }`
    : "No escalation updates recorded yet";

  const unreadLabel = summary?.has_unread_events
    ? `${pluralize(summary.unread_count, "unread update")}`
    : "All escalation updates reviewed";

  return (
    <section className="section-card" data-testid="patient-escalation-summary">
      <div className="section-header">
        <div>
          <p className="eyebrow">Operational snapshot</p>
          <h2 className="section-title">Escalation summary</h2>
        </div>
        <span className={`badge ${badge.variant}`}>{badge.label}</span>
      </div>
      <dl className="definition-list">
        <div className="definition-item">
          <dt>Active status</dt>
          <dd data-testid="patient-escalation-summary-status">{formatStatus(evidence, summary)}</dd>
        </div>
        <div className="definition-item">
          <dt>Priority</dt>
          <dd>{formatPriority(priority)}</dd>
        </div>
        <div className="definition-item">
          <dt>SLA / due state</dt>
          <dd>{slaDue ? formatDueDate(slaDue) : "No SLA scheduled"}</dd>
        </div>
        <div className="definition-item">
          <dt>Open work</dt>
          <dd>{openWorkLabel}</dd>
        </div>
        <div className="definition-item">
          <dt>Latest escalation update</dt>
          <dd>{latestUpdateLabel}</dd>
        </div>
        <div className="definition-item">
          <dt>Queue review</dt>
          <dd>{unreadLabel}</dd>
        </div>
      </dl>
    </section>
  );
}
