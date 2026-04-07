import { formatEventType } from "../../lib/format";
import { FILTER_LABELS } from "../../lib/statusLabels";

type Props = {
  patientId: string;
  eventTypes: string[];
  includeOnlyOpenWork: boolean;
  relatedEscalationId?: string | null;
  activeEscalationId?: string | null;
  pageSize?: number;
};

const EVENT_TYPE_OPTIONS: string[] = [
  "signal_recorded",
  "escalation_triggered",
  "escalation_status_changed",
  "escalation_sla_at_risk",
  "escalation_sla_overdue",
  "intervention_task_created",
  "intervention_task_due_upcoming",
  "intervention_task_due_overdue",
  "intervention_task_outcome_logged",
  "care_update_logged",
];

export default function TimelineFilters({
  patientId,
  eventTypes,
  includeOnlyOpenWork,
  relatedEscalationId,
  activeEscalationId,
  pageSize,
}: Props) {
  const action = `/patients/${patientId}`;
  const activeEscalationChecked =
    activeEscalationId != null && relatedEscalationId === activeEscalationId;

  return (
    <form className="timeline-filter-form" method="get" action={action}>
      {pageSize ? <input type="hidden" name="limit" value={String(pageSize)} /> : null}
      <div className="timeline-filter-fields">
        <fieldset className="timeline-filter-fieldset">
          <legend>Event types</legend>
          <div className="timeline-filter-options">
            {EVENT_TYPE_OPTIONS.map((value) => (
              <label key={value} className="checkbox">
                <input
                  type="checkbox"
                  name="event_types"
                  value={value}
                  defaultChecked={eventTypes.includes(value)}
                />
                <span>{formatEventType(value)}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <div className="timeline-filter-toggles">
          <label className="checkbox">
            <input
              type="checkbox"
              name="include_only_open_work"
              value="1"
              defaultChecked={includeOnlyOpenWork}
            />
            <span>{FILTER_LABELS.openWorkOnly}</span>
          </label>
          {activeEscalationId ? (
            <label className="checkbox">
              <input
                type="checkbox"
                name="related_escalation_id"
                value={activeEscalationId}
                defaultChecked={activeEscalationChecked}
              />
              <span>{FILTER_LABELS.activeEscalationOnly}</span>
            </label>
          ) : null}
        </div>
      </div>
      <div className="timeline-filter-actions">
        <button type="submit" className="button button--primary">
          Apply filters
        </button>
        <a className="button button--ghost" href={action}>
          Clear filters
        </a>
      </div>
    </form>
  );
}
