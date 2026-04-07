import { FILTER_LABELS } from "../../lib/statusLabels";

type Props = {
  activeOnly: boolean;
  hasUnreadOnly: boolean;
  patientIdsText: string;
  preservedParams?: Record<string, string | string[]>;
};

export default function WorklistControls({
  activeOnly,
  hasUnreadOnly,
  patientIdsText,
  preservedParams = {},
}: Props) {
  return (
    <form method="get" action="/patients" className="worklist-controls">
      <div className="worklist-controls-group">
        <span className="worklist-controls-label">Queue view</span>
        <label className="worklist-controls-option">
          <input type="radio" name="active_only" value="1" defaultChecked={activeOnly} />
          <span>Active queue</span>
        </label>
        <label className="worklist-controls-option">
          <input type="radio" name="active_only" value="0" defaultChecked={!activeOnly} />
          <span>All patients</span>
        </label>
      </div>
      <div className="worklist-controls-group">
        <span className="worklist-controls-label">Attention filters</span>
        <label className="worklist-controls-option">
          <input
            type="checkbox"
            name="has_unread_events"
            value="1"
            defaultChecked={hasUnreadOnly}
          />
          <span>{FILTER_LABELS.unreadOnly}</span>
        </label>
      </div>
      <div className="worklist-controls-group worklist-controls-grow">
        <label className="worklist-controls-label" htmlFor="patient_ids">
          Patient IDs (comma-separated)
        </label>
        <input
          id="patient_ids"
          name="patient_ids"
          type="text"
          placeholder="e.g. P123, P456"
          defaultValue={patientIdsText}
        />
      </div>
      {Object.entries(preservedParams).map(([key, value]) =>
        Array.isArray(value) ? (
          value.map((entry, index) => (
            <input key={`${key}-${entry}-${index}`} type="hidden" name={key} value={entry} />
          ))
        ) : (
          <input key={key} type="hidden" name={key} value={value} />
        ),
      )}
      <div className="worklist-controls-actions">
        <button type="submit" className="button">
          Apply filters
        </button>
        <a href="/patients" className="button button--ghost">
          Reset
        </a>
      </div>
    </form>
  );
}
