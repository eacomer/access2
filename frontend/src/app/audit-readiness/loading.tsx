export default function AuditReadinessLoading() {
  return (
    <main className="page" data-testid="audit-readiness-loading">
      <header className="patient-workflow-header">
        <div className="patient-workflow-header-main">
          <p className="eyebrow">ACCESS review packets</p>
          <h1>Audit readiness</h1>
          <p className="patient-workflow-header-subtitle">Loading persisted audit-readiness rows.</p>
        </div>
      </header>
      <section className="section-card">
        <p className="worklist-context-label">Loading</p>
        <p className="worklist-context-helper">Fetching latest-per-patient audit readiness from the backend.</p>
      </section>
    </main>
  );
}
