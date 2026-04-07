import { formatDateTime, formatRelativeTimeCompact } from "../../lib/format";
import type { PatientTimelineItem } from "../../types/patient";

type Props = {
  event: PatientTimelineItem;
  summary?: string | null;
  titleId?: string;
  subtitleId?: string;
  timestampId?: string;
  contextId?: string;
};

const FALLBACK_TITLE = "Timeline event";

const buildMetaSnippet = (event: PatientTimelineItem): string | null => {
  const metadata = event.metadata ?? {};
  const snippet =
    metadata.note ??
    metadata.description ??
    metadata.summary ??
    metadata.status ??
    null;
  if (typeof snippet === "string") {
    const trimmed = snippet.trim();
    return trimmed.length ? trimmed : null;
  }
  return null;
};

const getActorLabel = (event: PatientTimelineItem): string | null => {
  const metadata = event.metadata ?? {};
  const candidates = [
    metadata.actor_display_name,
    metadata.actor_name,
    metadata.author_name,
    metadata.assigned_to,
    metadata.reviewed_by,
    metadata.source_name,
  ];
  for (const candidate of candidates) {
    if (typeof candidate === "string") {
      const trimmed = candidate.trim();
      if (trimmed.length > 0) {
        return trimmed;
      }
    }
  }
  return null;
};

export default function TimelineRowSummary({
  event,
  summary,
  titleId,
  subtitleId,
  timestampId,
  contextId,
}: Props) {
  const subtitle =
    summary && summary.trim().length > 0 ? summary : buildMetaSnippet(event);
  const hasTimestamp = Boolean(event.occurred_at);
  const absoluteTimestamp = hasTimestamp ? formatDateTime(event.occurred_at) : "Unknown time";
  const relativeTimestamp = hasTimestamp ? formatRelativeTimeCompact(event.occurred_at) : "Unknown time";
  const actorLabel = getActorLabel(event);
  const contextParts: string[] = [];
  if (actorLabel) {
    contextParts.push(actorLabel);
  }
  if (hasTimestamp) {
    contextParts.push(absoluteTimestamp);
  }

  return (
    <div className="timeline-row-summary-block">
      <div className="timeline-row-summary-main">
        <p className="timeline-row-title" id={titleId}>
          {event.display_title || FALLBACK_TITLE}
        </p>
        <time
          className="timeline-row-timestamp"
          id={timestampId}
          dateTime={event.occurred_at ?? undefined}
          title={absoluteTimestamp}
        >
          {relativeTimestamp}
        </time>
      </div>
      {subtitle ? (
        <p className="timeline-row-subtitle" id={subtitleId}>
          {subtitle}
        </p>
      ) : null}
      {contextParts.length ? (
        <p className="timeline-row-context-meta" id={contextId}>
          {contextParts.join(" • ")}
        </p>
      ) : null}
    </div>
  );
}
