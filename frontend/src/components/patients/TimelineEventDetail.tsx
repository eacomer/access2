import {
  formatDateTime,
  formatEventType,
  formatPriority,
  formatRelativeTimeCompact,
} from "../../lib/format";
import type { PatientTimelineItem } from "../../types/patient";
import TimelineEventBadges from "./TimelineEventBadges";

type Props = {
  event: PatientTimelineItem | null;
  selectedRowLabelId?: string | null;
  contextSummary?: string | null;
  emptyHints?: string[];
  hasVisibleTimelineEvents?: boolean;
  hasActiveFilters?: boolean;
};

type DetailEntry = {
  label: string;
  value: string;
};

const HUMANIZE_SEPARATOR = /[_:-]/;

const humanize = (value: unknown): string | null => {
  if (typeof value !== "string" || value.trim().length === 0) {
    return null;
  }
  return value
    .split(HUMANIZE_SEPARATOR)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
};

const formatBoolean = (value: unknown): string | null => {
  if (typeof value !== "boolean") {
    return null;
  }
  return value ? "Yes" : "No";
};

const formatDate = (value: unknown): string | null => {
  if (value === null || value === undefined) {
    return null;
  }
  if (value instanceof Date || typeof value === "string" || typeof value === "number") {
    return formatDateTime(value);
  }
  return null;
};

const formatDefault = (value: unknown): string | null => {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length ? trimmed : null;
  }
  if (typeof value === "number") {
    return value.toString();
  }
  if (value instanceof Date) {
    return formatDateTime(value);
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  return String(value);
};

const addEntry = (
  entries: DetailEntry[],
  seen: Set<string>,
  label: string,
  rawValue: unknown,
  formatter: (value: unknown) => string | null = formatDefault,
) => {
  if (seen.has(label)) {
    return;
  }
  const formatted = formatter(rawValue);
  if (!formatted) {
    return;
  }
  entries.push({ label, value: formatted });
  seen.add(label);
};

const buildRelationshipBadges = (event: PatientTimelineItem): DetailEntry[] => {
  const entries: DetailEntry[] = [];
  const seen = new Set<string>();
  addEntry(entries, seen, "Escalation ID", event.related_escalation_id);
  addEntry(entries, seen, "Task ID", event.related_task_id);
  addEntry(entries, seen, "Outcome ID", event.related_outcome_id);
  addEntry(entries, seen, "Care update ID", event.metadata?.care_update_id);
  return entries;
};

const buildKeyEvidenceEntries = (event: PatientTimelineItem): DetailEntry[] => {
  const entries: DetailEntry[] = [];
  const seen = new Set<string>();
  addEntry(entries, seen, "Workflow status", event.status, humanize);
  addEntry(entries, seen, "Priority", event.priority, (value) =>
    typeof value === "string" ? formatPriority(value) : null,
  );
  addEntry(entries, seen, "Authored by", event.authored_by_user_id);
  addEntry(entries, seen, "Actor", event.actor_user_id);
  addEntry(entries, seen, "Source kind", humanize(event.source_kind));
  addEntry(entries, seen, "Source ID", event.source_id);
  return entries;
};

const KNOWN_METADATA_FIELDS: Record<
  string,
  Array<{ key: string; label?: string; formatter?: (value: unknown) => string | null }>
> = {
  signal_recorded: [
    { key: "signal_type", formatter: humanize },
    { key: "signal_source", label: "Source" },
    { key: "signal_value_numeric", label: "Value" },
    { key: "signal_value_text", label: "Value text" },
    { key: "unit", label: "Unit" },
    { key: "notes", label: "Notes" },
  ],
  escalation_triggered: [
    { key: "escalation_type", label: "Escalation type" },
    { key: "severity", formatter: humanize },
    { key: "status", formatter: humanize },
    { key: "triggered_at", label: "Triggered at", formatter: formatDate },
    { key: "sla_due_at", label: "SLA due", formatter: formatDate },
    { key: "resolution_notes", label: "Resolution notes" },
    { key: "cancellation_notes", label: "Cancellation notes" },
  ],
  escalation_status_changed: [
    { key: "status", formatter: humanize },
    { key: "note", label: "Note" },
  ],
  escalation_sla_at_risk: [
    { key: "sla_state", label: "SLA state", formatter: humanize },
    { key: "sla_due_at", label: "SLA due", formatter: formatDate },
    { key: "severity", formatter: humanize },
    { key: "escalation_status", label: "Escalation status", formatter: humanize },
  ],
  escalation_sla_overdue: [
    { key: "sla_state", label: "SLA state", formatter: humanize },
    { key: "sla_due_at", label: "SLA due", formatter: formatDate },
    { key: "severity", formatter: humanize },
    { key: "escalation_status", label: "Escalation status", formatter: humanize },
  ],
  intervention_task_created: [
    { key: "description", label: "Description" },
    { key: "due_at", label: "Due at", formatter: formatDate },
    { key: "assigned_user_id", label: "Assigned user" },
    { key: "completed_at", label: "Completed at", formatter: formatDate },
    { key: "completion_note", label: "Completion note" },
  ],
  intervention_task_due_upcoming: [
    { key: "due_state", label: "Due state", formatter: humanize },
    { key: "due_at", label: "Due at", formatter: formatDate },
    { key: "assigned_user_id", label: "Assigned user" },
    { key: "priority", formatter: (value) => (typeof value === "string" ? formatPriority(value) : null) },
    { key: "status", formatter: humanize },
  ],
  intervention_task_due_overdue: [
    { key: "due_state", label: "Due state", formatter: humanize },
    { key: "due_at", label: "Due at", formatter: formatDate },
    { key: "assigned_user_id", label: "Assigned user" },
    { key: "priority", formatter: (value) => (typeof value === "string" ? formatPriority(value) : null) },
    { key: "status", formatter: humanize },
  ],
  intervention_task_outcome_logged: [
    { key: "intervention_type", label: "Intervention type", formatter: humanize },
    { key: "completion_summary", label: "Completion summary" },
    { key: "patient_response", label: "Patient response" },
    { key: "follow_up_required", label: "Follow-up required", formatter: formatBoolean },
    { key: "follow_up_notes", label: "Follow-up notes" },
  ],
  care_update_logged: [
    { key: "care_update_type", label: "Update type", formatter: humanize },
    { key: "details", label: "Details" },
  ],
};

const buildMetadataEntries = (event: PatientTimelineItem): DetailEntry[] => {
  const metadata = event.metadata ?? {};
  const entries: DetailEntry[] = [];
  const seen = new Set<string>();

  const eventFields = KNOWN_METADATA_FIELDS[event.event_type] ?? [];
  for (const field of eventFields) {
    const { key, label, formatter } = field;
    addEntry(entries, seen, label ?? humanize(key) ?? key, metadata[key], formatter);
  }

  for (const [rawKey, rawValue] of Object.entries(metadata)) {
    const label = humanize(rawKey) ?? rawKey;
    addEntry(entries, seen, label, rawValue);
  }

  return entries;
};

const renderSummary = (event: PatientTimelineItem): string | null => {
  if (event.display_text && event.display_text.trim().length > 0) {
    return event.display_text.trim();
  }
  const metadata = event.metadata ?? {};
  const fallbackKeys = ["description", "notes", "completion_summary", "details", "signal_value_text"];
  for (const key of fallbackKeys) {
    const value = metadata[key];
    if (typeof value === "string" && value.trim().length > 0) {
      return value.trim();
    }
  }
  return null;
};

export default function TimelineEventDetail({
  event,
  selectedRowLabelId,
  contextSummary,
  emptyHints = [],
  hasVisibleTimelineEvents = false,
  hasActiveFilters = false,
}: Props) {
  const summary = event ? renderSummary(event) : null;
  const relationshipEntries = event ? buildRelationshipBadges(event) : [];
  const keyEvidenceEntries = event ? buildKeyEvidenceEntries(event) : [];
  const metadataEntries = event ? buildMetadataEntries(event) : [];
  const headingId = "timeline-event-detail-heading";
  const descriptionId = event ? "timeline-event-detail-description" : "timeline-event-detail-empty";
  const regionDescribedBy = [descriptionId, selectedRowLabelId].filter(Boolean).join(" ") || undefined;
  const detailTitle = event?.display_title?.trim().length ? event.display_title : "Timeline event";
  const occurredLabel = event?.occurred_at ? formatDateTime(event.occurred_at) : "Unknown time";
  const relativeOccurred = event?.occurred_at ? formatRelativeTimeCompact(event.occurred_at) : null;
  const occurredDisplay = relativeOccurred ? `${relativeOccurred} · ${occurredLabel}` : occurredLabel;
  const emptyTitle = hasVisibleTimelineEvents
    ? "Select a timeline event"
    : hasActiveFilters
      ? "Filters returned no timeline evidence"
      : "No timeline evidence yet";
  const emptyBody = hasVisibleTimelineEvents
    ? "Choose an event in the list to review its evidence."
    : hasActiveFilters
      ? "Change or clear the filters to reload evidence."
      : "Signals, escalations, or care updates will populate this panel once they are recorded.";
  const hasEmptyHints = emptyHints.length > 0 || Boolean(contextSummary);

  return (
    <section
      className="section-card"
      id="timeline-event-detail"
      role="region"
      aria-live="polite"
      aria-labelledby={headingId}
      aria-describedby={regionDescribedBy}
    >
      <div className="section-header">
        <div>
          <p className="eyebrow">Event detail</p>
          <h2 className="section-title" id={headingId}>
            Selected evidence
          </h2>
          <p className="section-subtitle">
            {event
              ? "Review metadata for the selected timeline event."
              : "Choose a timeline event to populate this evidence view."}
          </p>
        </div>
      </div>
      {!event ? (
        <div className="event-detail-empty" id={descriptionId}>
          <p className="event-detail-empty-title">{emptyTitle}</p>
          <p className="event-detail-empty-body">{emptyBody}</p>
          {hasEmptyHints ? (
            <div className="event-detail-empty-context">
              {emptyHints.length ? (
                <div className="event-detail-empty-hints">
                  {emptyHints.map((hint) => (
                    <span className="event-detail-empty-chip" key={hint}>
                      {hint}
                    </span>
                  ))}
                </div>
              ) : null}
              {contextSummary ? (
                <p className="event-detail-empty-summary">{contextSummary}</p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="event-detail">
          <p className="event-detail-context" id={descriptionId}>
            Showing evidence for <span className="event-detail-context-strong">{detailTitle}</span> ·{" "}
            <time dateTime={event.occurred_at ?? undefined}>{occurredDisplay}</time>
          </p>
          <div className="event-detail-header">
            <div>
              <p className="event-detail-type">{formatEventType(event.event_type)}</p>
              <h3 className="event-detail-title">{detailTitle}</h3>
            </div>
            <p className="event-detail-timestamp">{occurredDisplay}</p>
          </div>
          <TimelineEventBadges event={event} />
          {summary ? <p className="event-detail-summary">{summary}</p> : null}
          {relationshipEntries.length > 0 ? (
            <div className="event-detail-relationships">
              {relationshipEntries.map((entry) => (
                <div className="event-detail-chip" key={`relationship-${entry.label}`}>
                  <span className="event-detail-chip-label">{entry.label}</span>
                  <span className="event-detail-chip-value">{entry.value}</span>
                </div>
              ))}
            </div>
          ) : null}
          {keyEvidenceEntries.length > 0 ? (
            <div className="event-detail-section">
              <p className="event-detail-section-title">Key evidence</p>
              <dl className="event-detail-list">
                {keyEvidenceEntries.map((entry) => (
                  <div className="event-detail-item" key={`key-${entry.label}`}>
                    <dt>{entry.label}</dt>
                    <dd>{entry.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : null}
          {metadataEntries.length > 0 ? (
            <div className="event-detail-section">
              <p className="event-detail-section-title">Additional details</p>
              <dl className="event-detail-list">
                {metadataEntries.map((entry) => (
                  <div className="event-detail-item" key={`metadata-${entry.label}`}>
                    <dt>{entry.label}</dt>
                    <dd>{entry.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
