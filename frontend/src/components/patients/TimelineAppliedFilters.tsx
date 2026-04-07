type FilterChip = {
  id: string;
  label: string;
  href: string;
};

type Props = {
  chips: FilterChip[];
  clearHref?: string | null;
};

export default function TimelineAppliedFilters({ chips, clearHref }: Props) {
  if (!chips.length) {
    return null;
  }

  return (
    <section className="applied-filters" aria-label="Queue filters">
      <div className="applied-filters-left">
        <p className="worklist-context-label applied-filters-label">Queue filters</p>
        <div className="applied-filters-chips">
          {chips.map((chip) => (
            <a
              key={chip.id}
              href={chip.href}
              aria-label={`Remove filter ${chip.label}`}
              className="filter-chip-pill"
            >
              <span>{chip.label}</span>
              <span aria-hidden="true" className="filter-chip-pill-remove">
                ×
              </span>
            </a>
          ))}
        </div>
      </div>
      {clearHref ? (
        <a href={clearHref} className="button button--ghost">
          Clear all filters
        </a>
      ) : null}
    </section>
  );
}
