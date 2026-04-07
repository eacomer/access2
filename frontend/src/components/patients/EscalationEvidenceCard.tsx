import { formatDateTime, formatDueDate, formatEventType, formatPriority } from "../../lib/format";
import type { PatientEscalationEvidence } from "../../types/patient";

type Props = {
  evidence: PatientEscalationEvidence | null;
};

const getBadge = (evidence: PatientEscalationEvidence | null) => {
  if (!evidence) {
    return { label: "Evidence unavailable", variant: "badge--info" };
  }
  if (evidence.overdue_escalation_count > 0) {
    return { label: `${evidence.overdue_escalation_count} overdue`, variant: "badge--critical" };
  }
  if (evidence.at_risk_escalation_count > 0) {
    return { label: `${evidence.at_risk_escalation_count} at risk`, variant: "badge--warning" };
  }
  if (evidence.has_open_escalation) {
    return { label: "Open but within SLA", variant: "badge--info" };
  }
  return { label: "All clear", variant: "badge--positive" };
};

export default function EscalationEvidenceCard({ evidence }: Props) {
  const badge = getBadge(evidence);

  return (
    <section className="section-card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Queue context</p>
          <h2 className="section-title">Escalation evidence</h2>
        </div>
        <span className={`badge ${badge.variant}`}>{badge.label}</span>
      </div>
      {!evidence ? (
        <p className="empty-state">
          Escalation evidence is not available for this patient yet. Refresh once new signals arrive.
        </p>
      ) : (
        <>
          <div className="evidence-grid">
            <div className="count-block">
              <span className="count-label">Open escalations</span>
              <span className="count-value">{evidence.open_escalation_count}</span>
            </div>
            <div className="count-block">
              <span className="count-label">Overdue</span>
              <span className="count-value">{evidence.overdue_escalation_count}</span>
            </div>
            <div className="count-block">
              <span className="count-label">At risk</span>
              <span className="count-value">{evidence.at_risk_escalation_count}</span>
            </div>
          </div>
          <dl className="definition-list">
            <div className="definition-item">
              <dt>Highest priority</dt>
              <dd>{formatPriority(evidence.highest_open_escalation_priority)}</dd>
            </div>
            <div className="definition-item">
              <dt>Next SLA due</dt>
              <dd>{formatDueDate(evidence.next_open_escalation_sla_due_at)}</dd>
            </div>
            <div className="definition-item">
              <dt>Latest open escalation status</dt>
              <dd>{evidence.latest_open_escalation_status ?? "Not available"}</dd>
            </div>
            <div className="definition-item">
              <dt>Latest escalation event</dt>
              <dd>
                {evidence.latest_escalation_event_type
                  ? `${formatEventType(evidence.latest_escalation_event_type)} · ${formatDateTime(
                      evidence.latest_escalation_event_occurred_at,
                    )}`
                  : "Not available"}
              </dd>
            </div>
          </dl>
        </>
      )}
    </section>
  );
}
