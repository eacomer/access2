import SignOutButton from "../SignOutButton";

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
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <p className="eyebrow">Patient queue</p>
        <SignOutButton />
      </div>
      <div className="patient-workflow-header-main">
        <h1>{title}</h1>
        <p className="patient-workflow-header-subtitle">{description}</p>
        {subtitle ? <p className="lede">{subtitle}</p> : null}
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
