import Link from "next/link";
import type { ReactElement } from "react";

import { formatDateTime, formatDayGrouping, formatEventType, formatPriority } from "../../lib/format";
import type { PatientTimelineItem } from "../../types/patient";
import TimelineEventBadges from "./TimelineEventBadges";
import TimelineRowSummary from "./TimelineRowSummary";

type Props = {
  events: PatientTimelineItem[];
  patientId: string;
  selectedEventId?: string;
  baseQueryString?: string;
  hasAnyEvents: boolean;
  isFiltered?: boolean;
  clearFiltersHref?: string | null;
};

type MetadataEntry = {
  label: string;
  value: string;
};

const MAX_METADATA_ENTRIES = 4;

type EventCategory =
  | { id: "escalation"; label: string; tone?: "info" | "warning" | "alert" }
  | { id: "task"; label: string; tone?: "info" | "warning" | "alert" }
  | { id: "care"; label: string; tone?: "info" | "warning" | "alert" }
  | { id: "signal"; label: string; tone?: "info" | "warning" | "alert" }
  | { id: "general"; label: string; tone?: "info" | "warning" | "alert" };

type StatusTone = "info" | "warning" | "alert" | "positive";

const asTrimmedString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
};

const humanize = (value: unknown): string | null => {
  if (typeof value !== "string" || value.length === 0) {
    return null;
  }
  return value
    .split(/[_:-]/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
};

const formatBooleanValue = (value: unknown): string | null => {
  if (typeof value !== "boolean") {
    return null;
  }
  return value ? "Yes" : "No";
};

const formatDateValue = (value: unknown): string | null => {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string" || typeof value === "number" || value instanceof Date) {
    return formatDateTime(value);
  }
  return null;
};

const formatDefaultValue = (value: unknown): string | null => {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string") {
    return asTrimmedString(value);
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

const signalValue = (metadata: Record<string, unknown>): string | null => {
  const numeric = typeof metadata.signal_value_numeric === "number" ? metadata.signal_value_numeric : null;
  const unit = asTrimmedString(metadata.unit);
  const text = asTrimmedString(metadata.signal_value_text);
  const pieces: string[] = [];
  if (numeric !== null) {
    pieces.push(unit ? `${numeric} ${unit}` : `${numeric}`);
  }
  if (text) {
    pieces.push(text);
  }
  return pieces.length ? pieces.join(" · ") : null;
};

const metaString = (metadata: Record<string, unknown>, key: string): string | null => {
  return asTrimmedString(metadata[key]);
};

const addEntry = (
  entries: MetadataEntry[],
  label: string,
  rawValue: unknown,
  formatter: (value: unknown) => string | null = formatDefaultValue,
) => {
  if (entries.length >= MAX_METADATA_ENTRIES) {
    return;
  }
  const formatted = formatter(rawValue);
  if (formatted) {
    entries.push({ label, value: formatted });
  }
};

const buildMetadataEntries = (event: PatientTimelineItem): MetadataEntry[] => {
  const metadata = event.metadata ?? {};
  const entries: MetadataEntry[] = [];

  addEntry(entries, "Status", event.status, humanize);
  if (event.priority) {
    addEntry(entries, "Priority", event.priority, (value) =>
      typeof value === "string" ? formatPriority(value) : null,
    );
  }

  switch (event.event_type) {
    case "signal_recorded":
      addEntry(entries, "Signal type", metadata.signal_type, humanize);
      addEntry(entries, "Source", metadata.signal_source);
      addEntry(entries, "Value", signalValue(metadata));
      addEntry(entries, "Notes", metadata.notes);
      break;
    case "escalation_triggered":
      addEntry(entries, "Severity", metadata.severity ?? event.priority, humanize);
      addEntry(entries, "SLA due", metadata.sla_due_at, formatDateValue);
      break;
    case "escalation_status_changed":
      addEntry(entries, "New status", metadata.status ?? event.status, humanize);
      addEntry(entries, "Note", metadata.note);
      break;
    case "escalation_sla_at_risk":
    case "escalation_sla_overdue":
      addEntry(entries, "SLA due", metadata.sla_due_at, formatDateValue);
      addEntry(entries, "Severity", metadata.severity ?? event.priority, humanize);
      addEntry(entries, "Escalation status", metadata.escalation_status ?? event.status, humanize);
      break;
    case "intervention_task_created":
      addEntry(entries, "Due at", metadata.due_at, formatDateValue);
      addEntry(entries, "Assigned", metaString(metadata, "assigned_user_id"));
      break;
    case "intervention_task_due_upcoming":
    case "intervention_task_due_overdue":
      addEntry(entries, "Due at", metadata.due_at, formatDateValue);
      addEntry(entries, "Due state", metadata.due_state, humanize);
      break;
    case "intervention_task_outcome_logged":
      addEntry(entries, "Intervention", metadata.intervention_type, humanize);
      addEntry(entries, "Follow up", metadata.follow_up_required, formatBooleanValue);
      addEntry(entries, "Patient response", metadata.patient_response);
      break;
    case "care_update_logged":
      addEntry(entries, "Update type", metadata.care_update_type, humanize);
      break;
    default:
      break;
  }

  return entries;
};

const buildEventSummary = (event: PatientTimelineItem): string | null => {
  if (event.display_text) {
    const trimmed = event.display_text.trim();
    if (trimmed.length > 0) {
      return trimmed;
    }
  }
  const metadata = event.metadata ?? {};
  return (
    metaString(metadata, "note") ??
    metaString(metadata, "description") ??
    metaString(metadata, "reason") ??
    metaString(metadata, "completion_summary") ??
    metaString(metadata, "details") ??
    null
  );
};

const getDayKey = (value?: string | null): string => {
  if (!value) {
    return "unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "unknown";
  }
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
};

const getEventCategory = (eventType: string): EventCategory => {
  if (eventType.startsWith("escalation_")) {
    if (eventType.includes("overdue")) {
      return { id: "escalation", label: "Escalation SLA", tone: "alert" };
    }
    if (eventType.includes("sla_at_risk")) {
      return { id: "escalation", label: "Escalation SLA", tone: "warning" };
    }
    return { id: "escalation", label: "Escalation workflow", tone: "info" };
  }
  if (eventType.startsWith("intervention_task")) {
    if (eventType.includes("overdue")) {
      return { id: "task", label: "Task overdue", tone: "alert" };
    }
    if (eventType.includes("due_upcoming")) {
      return { id: "task", label: "Task due soon", tone: "warning" };
    }
    return { id: "task", label: "Task workflow", tone: "info" };
  }
  if (eventType.startsWith("care_update")) {
    return { id: "care", label: "Care update" };
  }
  if (eventType.startsWith("signal_")) {
    return { id: "signal", label: "Signal evidence" };
  }
  return { id: "general", label: "Workflow evidence" };
};

const STATUS_FIELD_LABELS = new Set([
  "Status",
  "New status",
  "Priority",
  "Severity",
  "SLA due",
  "Due at",
  "Due state",
  "Escalation status",
]);

const inferStatusTone = (label: string, value: string): StatusTone | undefined => {
  const text = `${label} ${value}`.toLowerCase();
  if (text.includes("overdue") || text.includes("violation") || text.includes("critical")) {
    return "alert";
  }
  if (text.includes("risk") || text.includes("due soon") || text.includes("high")) {
    return "warning";
  }
  if (text.includes("resolved") || text.includes("completed") || text.includes("clear")) {
    return "positive";
  }
  if (text.includes("open") || text.includes("in progress") || text.includes("acknowledged")) {
    return "info";
  }
  return undefined;
};

export default function TimelineList({
  events,
  patientId,
  selectedEventId,
  baseQueryString,
  hasAnyEvents,
  isFiltered = false,
  clearFiltersHref = null,
}: Props) {
  if (events.length === 0) {
    if (!hasAnyEvents) {
      return (
        <div className="timeline-empty">
          <p className="timeline-empty-title">No timeline evidence recorded</p>
          <p className="timeline-empty-body">
            This patient has not generated timeline events yet. Incoming signals, escalations, or care
            updates will land here once captured.
          </p>
        </div>
      );
    }

    if (isFiltered) {
      return (
        <div className="timeline-empty">
          <p className="timeline-empty-title">Filters returned no timeline events</p>
          <p className="timeline-empty-body">Update or clear the filters to review all evidence.</p>
          {clearFiltersHref ? (
            <Link href={clearFiltersHref} className="timeline-empty-link">
              Clear all timeline filters
            </Link>
          ) : null}
        </div>
      );
    }

    return (
      <div className="timeline-empty">
        <p className="timeline-empty-title">No events on this page</p>
        <p className="timeline-empty-body">
          Use the pagination controls to move to newer or older evidence.
        </p>
      </div>
    );
  }

  const renderedEvents: ReactElement[] = [];
  let previousDayKey: string | null = null;

  events.forEach((event) => {
    const dayKey = getDayKey(event.occurred_at);
    if (dayKey !== previousDayKey) {
      const dayLabel = formatDayGrouping(event.occurred_at);
      renderedEvents.push(
        <li key={`day-${dayKey}-${event.event_id}`} className="timeline-day-separator">
          <span className="timeline-day-separator-line" aria-hidden="true" />
          <span className="timeline-day-separator-label">{dayLabel}</span>
          <span className="timeline-day-separator-line" aria-hidden="true" />
        </li>,
      );
      previousDayKey = dayKey;
    }

    const isSelected = event.event_id === selectedEventId;
    const query = new URLSearchParams(baseQueryString ?? "");
    query.set("eventId", event.event_id);
    const hrefQuery = query.toString();
    const href =
      hrefQuery.length > 0
        ? `/patients/${patientId}?${hrefQuery}`
        : `/patients/${patientId}?eventId=${encodeURIComponent(event.event_id)}`;
    const metadataEntries = buildMetadataEntries(event);
    const statusEntries: MetadataEntry[] = [];
    const detailEntries: MetadataEntry[] = [];
    metadataEntries.forEach((entry) => {
      if (STATUS_FIELD_LABELS.has(entry.label)) {
        statusEntries.push(entry);
      } else {
        detailEntries.push(entry);
      }
    });
    const summary = buildEventSummary(event);
    const rowBaseId = `timeline-${event.event_id}`;
    const titleId = `${rowBaseId}-title`;
    const timestampId = `${rowBaseId}-timestamp`;
    const subtitleId = summary ? `${rowBaseId}-subtitle` : undefined;
    const metadataId = detailEntries.length ? `${rowBaseId}-meta` : undefined;
    const statuslineId = statusEntries.length ? `${rowBaseId}-statusline` : undefined;
    const contextId = `${rowBaseId}-context`;
    const describedBy: string[] = [];
    if (subtitleId) {
      describedBy.push(subtitleId);
    }
    if (statuslineId) {
      describedBy.push(statuslineId);
    }
    if (metadataId) {
      describedBy.push(metadataId);
    }
    describedBy.push(contextId);
    const describedByAttr = describedBy.length ? describedBy.join(" ") : undefined;
    const category = getEventCategory(event.event_type);
    const rowClassNames = [
      "timeline-row",
      `timeline-row--${category.id}`,
      category.tone ? `timeline-row--${category.tone}` : null,
      isSelected ? "selected" : null,
    ]
      .filter(Boolean)
      .join(" ");

    renderedEvents.push(
      <li key={event.event_id}>
        <Link
          href={href}
          className={rowClassNames}
          id={rowBaseId}
          aria-current={isSelected ? "true" : undefined}
          aria-labelledby={titleId}
          aria-describedby={describedByAttr}
          aria-controls="timeline-event-detail"
        >
          <div className="timeline-row-head">
            <span
              className={`timeline-event-type-chip timeline-event-type-chip--${category.id}${
                category.tone ? ` timeline-event-type-chip--${category.tone}` : ""
              }`}
            >
              {formatEventType(event.event_type)}
            </span>
            <span className="timeline-event-category">{category.label}</span>
          </div>
          <div className="timeline-row-body">
            <TimelineRowSummary
              event={event}
              summary={summary}
              titleId={titleId}
              subtitleId={subtitleId}
              timestampId={timestampId}
              contextId={contextId}
            />
            <div className="timeline-row-evidence-context">
              {statusEntries.length ? (
                <div className="timeline-row-statusline" id={statuslineId}>
                  {statusEntries.map((entry) => {
                    const tone = inferStatusTone(entry.label, entry.value);
                    return (
                      <span
                        key={`${event.event_id}-${entry.label}`}
                        className={`timeline-status-chip${tone ? ` timeline-status-chip--${tone}` : ""}`}
                      >
                        <span className="timeline-status-chip-label">{entry.label}</span>
                        <span className="timeline-status-chip-value">{entry.value}</span>
                      </span>
                    );
                  })}
                </div>
              ) : null}
              <TimelineEventBadges event={event} />
            </div>
            {detailEntries.length ? (
              <dl className="timeline-row-meta" id={metadataId}>
                {detailEntries.map((entry) => (
                  <div className="timeline-row-meta-item" key={`${event.event_id}-${entry.label}`}>
                    <dt>{entry.label}</dt>
                    <dd>{entry.value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>
        </Link>
      </li>,
    );
  });

  return <ul className="timeline-list">{renderedEvents}</ul>;
}
