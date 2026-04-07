type Props = {
  hasFilters: boolean;
  clearHref?: string | null;
};

export default function WorklistEmptyState({ hasFilters, clearHref }: Props) {
  if (hasFilters) {
    return (
      <div className="timeline-empty worklist-empty">
        <p className="timeline-empty-title">No patients match these filters</p>
        <p className="timeline-empty-body">Adjust or clear the filters to return to the active queue.</p>
        {clearHref ? (
          <a href={clearHref} className="timeline-empty-link">
            Clear worklist filters
          </a>
        ) : null}
      </div>
    );
  }

  return (
    <div className="timeline-empty worklist-empty">
      <p className="timeline-empty-title">The queue is currently quiet</p>
      <p className="timeline-empty-body">No patients require action right now. New activity will appear here.</p>
    </div>
  );
}
