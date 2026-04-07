type HeaderChip = {
  id: string;
  label: string;
};

type Props = {
  title: string;
  subtitle: string;
  description: string;
  chips: HeaderChip[];
};

export default function WorklistHeader({ title, subtitle, description, chips }: Props) {
  return (
    <section className="patient-workflow-header">
      <div className="patient-workflow-header-main">
        <p className="eyebrow">Patient queue</p>
        <h1>{title}</h1>
        <p className="patient-workflow-header-subtitle">{description}</p>
      </div>
      {chips.length ? (
        <div className="patient-workflow-cues">
          {chips.map((chip) => (
            <div key={chip.id} className="patient-workflow-chip">
              <span className="patient-workflow-chip-label">Mode</span>
              <span className="patient-workflow-chip-value">{chip.label}</span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
