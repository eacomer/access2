type SearchParamsRecord = Record<string, string | string[] | undefined>;

type Props = {
  total: number;
  visibleCount: number;
  limit: number;
  skip: number;
  searchParams: SearchParamsRecord;
};

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const createSearchParams = (source: SearchParamsRecord, omitKeys: string[] = []) => {
  const params = new URLSearchParams();
  for (const [key, rawValue] of Object.entries(source)) {
    if (omitKeys.includes(key) || rawValue === undefined) {
      continue;
    }
    const values = Array.isArray(rawValue) ? rawValue : [rawValue];
    values.forEach((entry) => {
      if (entry !== undefined) {
        params.append(key, entry);
      }
    });
  }
  return params;
};

const toHref = (params: URLSearchParams) => {
  const query = params.toString();
  return query ? `/patients?${query}` : "/patients";
};

const buildDetailText = (limit: number, hasPrevious: boolean, hasNext: boolean) => {
  const parts = [`Window size ${limit}`];
  if (hasPrevious) {
    parts.push("Earlier patients behind");
  }
  if (hasNext) {
    parts.push("More patients ahead");
  }
  return parts.join(" • ");
};

export default function WorklistPaginationControls({
  total,
  visibleCount,
  limit,
  skip,
  searchParams,
}: Props) {
  if (visibleCount === 0) {
    return null;
  }

  const windowStart = skip + 1;
  const windowEnd = skip + visibleCount;
  const summary =
    total > 0
      ? `Showing patients ${windowStart}-${windowEnd} of ${total}`
      : `Showing ${visibleCount} patients`;

  const hasPrevious = skip > 0;
  const hasNext = windowEnd < total;

  const buildHrefWithSkip = (nextSkip: number) => {
    const params = createSearchParams(searchParams);
    if (nextSkip <= 0) {
      params.delete("skip");
    } else {
      params.set("skip", String(nextSkip));
    }
    return toHref(params);
  };

  const previousHref = hasPrevious ? buildHrefWithSkip(Math.max(0, skip - limit)) : null;
  const nextHref = hasNext ? buildHrefWithSkip(skip + limit) : null;

  const limitParams = createSearchParams(searchParams, ["limit", "skip"]);
  const hiddenInputs = Array.from(limitParams.entries()).map(([key, value], index) => (
    <input key={`${key}-${value}-${index}`} type="hidden" name={key} value={value} />
  ));

  const detailText = buildDetailText(limit, hasPrevious, hasNext);

  const pageSizeOptions = PAGE_SIZE_OPTIONS.includes(limit)
    ? PAGE_SIZE_OPTIONS
    : [...PAGE_SIZE_OPTIONS, limit].sort((a, b) => a - b);

  return (
    <section
      className="timeline-pagination worklist-pagination"
      aria-label="Queue window controls"
    >
      <div>
        <p className="worklist-context-label">Window controls</p>
        <p className="timeline-pagination-summary">{summary}</p>
        <p className="timeline-pagination-detail">{detailText}</p>
      </div>
      <div className="timeline-pagination-controls">
        <form className="timeline-pagination-limit" method="get" action="/patients">
          {hiddenInputs}
          <label>
            <span className="worklist-context-label">Window size</span>
            <select name="limit" defaultValue={String(limit)} className="form-control">
              {pageSizeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" className="button button--ghost">
            Update window
          </button>
        </form>
        <div className="timeline-pagination-nav">
          {previousHref ? (
            <a className="button button--ghost" href={previousHref}>
              ← Previous
            </a>
          ) : null}
          {nextHref ? (
            <a className="button" href={nextHref}>
              Next →
            </a>
          ) : null}
        </div>
      </div>
    </section>
  );
}
