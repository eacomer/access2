import { formatEventType } from "../../lib/format";
import type { PatientAttentionSummary } from "../../types/patient";

type Props = {
  summary: PatientAttentionSummary | null;
  statusSnapshot?: string | null;
  careGapLabel?: string | null;
  blockingIssueLabel?: string | null;
  resolutionTargetLabel?: string | null;
  closureReadinessLabel?: string | null;
  resolutionConfidenceLabel?: string | null;
  activeOwnerLabel?: string | null;
  waitingOnLabel?: string | null;
};

const badgeVariantForUrgency = (urgency?: string | null) => {
  if (urgency === "overdue" || urgency === "urgent") {
    return "badge--danger";
  }
  if (urgency === "active") {
    return "badge--warning";
  }
  return "badge--positive";
};

export default function PatientWhyNowSummary({
  summary,
  statusSnapshot,
  careGapLabel,
  blockingIssueLabel,
  resolutionTargetLabel,
  closureReadinessLabel,
  resolutionConfidenceLabel,
  activeOwnerLabel,
  waitingOnLabel,
}: Props) {
  const evidence = summary?.supporting_evidence?.filter(Boolean) ?? [];
  const urgencyLabel = summary?.urgency_level ? formatEventType(summary.urgency_level) : "Stable";

  return (
    <section className="section-card">
      <div className="section-header">
        <div>
          <p className="eyebrow">Why now</p>
          <h2 className="section-title">Recommended next action</h2>
          <p className="section-subtitle">
            {summary?.primary_driver ? formatEventType(summary.primary_driver) : "Monitoring"} driver
          </p>
        </div>
        <span className={`badge ${badgeVariantForUrgency(summary?.urgency_level)}`}>
          {urgencyLabel}
        </span>
      </div>

      <dl className="definition-list">
        {statusSnapshot ? (
          <div className="definition-item">
            <dt>Status snapshot</dt>
            <dd>{statusSnapshot}</dd>
          </div>
        ) : null}
        {careGapLabel ? (
          <div className="definition-item">
            <dt>Care gap</dt>
            <dd>{careGapLabel}</dd>
          </div>
        ) : null}
        {blockingIssueLabel ? (
          <div className="definition-item">
            <dt>Blocker</dt>
            <dd>{blockingIssueLabel}</dd>
          </div>
        ) : null}
        {activeOwnerLabel ? (
          <div className="definition-item">
            <dt>Owner</dt>
            <dd>{activeOwnerLabel}</dd>
          </div>
        ) : null}
        {waitingOnLabel ? (
          <div className="definition-item">
            <dt>Waiting on</dt>
            <dd>{waitingOnLabel}</dd>
          </div>
        ) : null}
        {resolutionTargetLabel ? (
          <div className="definition-item">
            <dt>Done when</dt>
            <dd>{resolutionTargetLabel}</dd>
          </div>
        ) : null}
        {closureReadinessLabel ? (
          <div className="definition-item">
            <dt>Closure readiness</dt>
            <dd>{closureReadinessLabel}</dd>
          </div>
        ) : null}
        {resolutionConfidenceLabel ? (
          <div className="definition-item">
            <dt>Resolution confidence</dt>
            <dd>{resolutionConfidenceLabel}</dd>
          </div>
        ) : null}
        <div className="definition-item">
          <dt>Why now</dt>
          <dd>{summary?.why_now ?? "No active workflow evidence is currently available."}</dd>
        </div>
        <div className="definition-item">
          <dt>Recommended next action</dt>
          <dd>{summary?.recommended_next_action ?? "Continue routine monitoring."}</dd>
        </div>
      </dl>

      <div>
        <h3 className="compact-panel-title">Supporting evidence</h3>
        {evidence.length ? (
          <ul className="compact-evidence-list">
            {evidence.map((item, index) => (
              <li key={`${item}-${index}`} className="compact-evidence-item">
                <p className="compact-evidence-title">{item}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty-state">No supporting workflow evidence recorded.</p>
        )}
      </div>
    </section>
  );
}
