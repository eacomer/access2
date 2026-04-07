type Props = {
  patientId: string;
  total: number;
  visibleCount: number;
  limit: number;
  hasMore: boolean;
  nextCursorOccurredAt: string | null;
  nextCursorEventId: string | null;
  resetQueryString: string;
  isPaged: boolean;
};

const PAGE_SIZE_OPTIONS = [10, 25, 50];

const buildHref = (patientId: string, queryString: string): string => {
  if (!queryString || queryString.length === 0) {
    return `/patients/${patientId}`;
  }
  return `/patients/${patientId}?${queryString}`;
};

export default function TimelinePaginationControls({
  patientId,
  total,
  visibleCount,
  limit,
  hasMore,
  nextCursorOccurredAt,
  nextCursorEventId,
  resetQueryString,
  isPaged,
}: Props) {
  if (visibleCount === 0 && total === 0) {
    return null;
  }

  const resetParams = new URLSearchParams(resetQueryString);
  const summary =
    total > 0 ? `Showing ${visibleCount} of ${total} events` : `Showing ${visibleCount} events`;
  const oldestLabel = hasMore ? "Older events available" : "End of recorded events";

  let olderHref: string | null = null;
  if (hasMore && nextCursorOccurredAt) {
    const olderParams = new URLSearchParams(resetParams.toString());
    olderParams.set("cursor_occurred_at", nextCursorOccurredAt);
    if (nextCursorEventId) {
      olderParams.set("cursor_event_id", nextCursorEventId);
    } else {
      olderParams.delete("cursor_event_id");
    }
    olderHref = buildHref(patientId, olderParams.toString());
  }

  const latestHref = buildHref(patientId, resetParams.toString());
  const showControls = hasMore || isPaged || total > limit;

  if (!showControls) {
    return (
      <div className="timeline-pagination">
        <p className="timeline-pagination-summary">{summary}</p>
        <p className="timeline-pagination-detail">{oldestLabel}</p>
      </div>
    );
  }

  const hiddenInputs = Array.from(resetParams.entries())
    .filter(([key]) => key !== "limit")
    .map(([key, value], index) => (
      <input key={`${key}-${value}-${index}`} type="hidden" name={key} value={value} />
    ));

  return (
    <div className="timeline-pagination">
      <div>
        <p className="timeline-pagination-summary">{summary}</p>
        <p className="timeline-pagination-detail">{oldestLabel}</p>
      </div>
      <div className="timeline-pagination-controls">
        <form className="timeline-pagination-limit" method="get" action={buildHref(patientId, "")}>
          {hiddenInputs}
          <label>
            <span>Page size</span>
            <select name="limit" defaultValue={String(limit)} className="form-control">
              {PAGE_SIZE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
              {!PAGE_SIZE_OPTIONS.includes(limit) ? (
                <option value={limit}>{limit}</option>
              ) : null}
            </select>
          </label>
          <button type="submit" className="button button--ghost">
            Apply
          </button>
        </form>
        <div className="timeline-pagination-nav">
          {isPaged ? (
            <a className="button button--ghost" href={latestHref}>
              Newest
            </a>
          ) : null}
          {olderHref ? (
            <a className="button" href={olderHref}>
              Older →
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}
