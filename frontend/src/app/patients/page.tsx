import WorklistSummaryCard from "../../components/patients/WorklistSummaryCard";
import { fetchWorklistSummary } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function PatientsPage() {
  const worklist = await fetchWorklistSummary({ limit: 25, activeOnly: true });

  return (
    <main className="page">
      <section className="page-header">
        <p className="eyebrow">Patient queue</p>
        <h1>Worklist</h1>
        <p className="lede">Escalation-aware cues that show who needs attention and why.</p>
      </section>
      {worklist.items.length === 0 ? (
        <section className="section-card">
          <p className="empty-state">No patients currently require attention.</p>
        </section>
      ) : (
        <div className="worklist-grid">
          {worklist.items.map((item) => (
            <WorklistSummaryCard key={item.patient_id} summary={item} />
          ))}
        </div>
      )}
    </main>
  );
}
