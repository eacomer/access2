type Props = {
  primary: string;
  detail: string;
  label?: string;
  helper?: string;
};

export default function WorklistStateSummary({
  primary,
  detail,
  label = "Queue snapshot",
  helper,
}: Props) {
  return (
    <section className="timeline-state worklist-state">
      <div className="worklist-context-header">
        <p className="worklist-context-label">{label}</p>
        {helper ? <p className="worklist-context-helper">{helper}</p> : null}
      </div>
      <p className="timeline-state-primary">{primary}</p>
      <p className="timeline-state-detail">{detail}</p>
    </section>
  );
}
