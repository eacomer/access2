import { formatDateTime, formatEventType, pluralize } from "../../lib/format";
import type {
  PatientInterventionEvidenceSummary,
  PatientInterventionEvidenceSummaryItem,
  PatientWorkflowStatusSummary,
} from "../../types/patient";

type Props = {
  summary: PatientInterventionEvidenceSummary | null;
  workflowStatus: PatientWorkflowStatusSummary | null;
};

const formatStatus = (status?: string | null) => {
  if (!status) {
    return null;
  }
  return formatEventType(status);
};

const renderItems = (
  items: PatientInterventionEvidenceSummaryItem[],
  emptyLabel: string,
) => {
  if (!items.length) {
    return <p className="empty-state">{emptyLabel}</p>;
  }

  return (
    <ul className="compact-evidence-list">
      {items.map((item, index) => {
        const status = formatStatus(item.status);
        const timestamp = item.occurred_at ? formatDateTime(item.occurred_at) : null;
        const meta = [status, timestamp].filter(Boolean).join(" · ");
        return (
          <li key={`${item.title}-${item.occurred_at ?? index}`} className="compact-evidence-item">
            <p className="compact-evidence-title">{item.title}</p>
            {meta ? <p className="compact-evidence-meta">{meta}</p> : null}
            {item.detail ? <p className="compact-evidence-detail">{item.detail}</p> : null}
          </li>
        );
      })}
    </ul>
  );
};

export default function PatientInterventionEvidenceSummary({
  summary,
  workflowStatus,
}: Props) {
  if (!summary) {
    return (
      <section className="section-card" data-testid="patient-intervention-summary">
        <div className="section-header">
          <div>
            <p className="eyebrow">Intervention evidence</p>
            <h2 className="section-title">Work summary</h2>
          </div>
        </div>
        <p className="empty-state">Intervention evidence is not available for this patient yet.</p>
      </section>
    );
  }

  const activeWork = summary.open_escalations + summary.open_tasks + summary.in_progress_tasks;
  const badge =
    activeWork > 0
      ? { label: pluralize(activeWork, "active work item"), variant: "badge--warning" }
      : { label: "No active work", variant: "badge--positive" };
  const taskState = [
    summary.open_tasks > 0 ? pluralize(summary.open_tasks, "open task") : null,
    summary.in_progress_tasks > 0
      ? pluralize(summary.in_progress_tasks, "task in progress")
      : null,
    summary.completed_tasks > 0 ? pluralize(summary.completed_tasks, "completed task") : null,
    summary.canceled_tasks > 0 ? pluralize(summary.canceled_tasks, "canceled task") : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className="section-card" data-testid="patient-intervention-summary">
      <div className="section-header">
        <div>
          <p className="eyebrow">Intervention evidence</p>
          <h2 className="section-title">Work summary</h2>
          <p className="section-subtitle">
            {workflowStatus?.label ?? "Monitoring"} · {pluralize(summary.evidence_event_count, "evidence event")}
          </p>
        </div>
        <span className={`badge ${badge.variant}`}>{badge.label}</span>
      </div>

      <dl className="definition-list">
        <div className="definition-item">
          <dt>Operational status</dt>
          <dd>{workflowStatus?.detail ?? workflowStatus?.label ?? "Monitoring"}</dd>
        </div>
        <div className="definition-item">
          <dt>Escalations</dt>
          <dd>
            {pluralize(summary.total_escalations, "total escalation")} ·{" "}
            {pluralize(summary.open_escalations, "open escalation")}
          </dd>
        </div>
        <div className="definition-item">
          <dt>Tasks</dt>
          <dd>{taskState || "No tasks recorded"}</dd>
        </div>
      </dl>

      <div className="compact-evidence-grid">
        <div>
          <h3 className="compact-panel-title">Why triggered</h3>
          {renderItems(summary.recent_trigger_reasons, "No escalation triggers recorded.")}
        </div>
        <div>
          <h3 className="compact-panel-title">Work completed</h3>
          {renderItems(summary.recent_completed_interventions, "No completed interventions recorded.")}
        </div>
        <div>
          <h3 className="compact-panel-title">Still open</h3>
          {renderItems(summary.current_open_work, "No open intervention work.")}
        </div>
      </div>
    </section>
  );
}
