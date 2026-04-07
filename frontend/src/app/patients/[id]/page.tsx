import Link from "next/link";

import EscalationEvidenceCard from "../../../components/patients/EscalationEvidenceCard";
import TimelineList from "../../../components/patients/TimelineList";
import { fetchPatientTimeline, fetchPatientTimelineEvent, fetchWorklistSummary } from "../../../lib/api";

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams?: Promise<{ eventId?: string | string[] }>;
};

export const dynamic = "force-dynamic";

export default async function PatientDetailPage({ params, searchParams }: PageProps) {
  const { id: patientId } = await params;
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const requestedEventId =
    typeof resolvedSearchParams?.eventId === "string" ? resolvedSearchParams.eventId : undefined;

  const [worklist, timeline] = await Promise.all([
    fetchWorklistSummary({ patientIds: [patientId], limit: 1 }),
    fetchPatientTimeline(patientId, { limit: 25 }),
  ]);

  const selectedEventId = requestedEventId ?? timeline.items[0]?.event_id;
  const detail = selectedEventId
    ? await fetchPatientTimelineEvent(patientId, selectedEventId)
    : null;
  const patientName = worklist.items[0]?.patient_display_name ?? detail?.item.patient_id ?? patientId;

  return (
    <main className="page">
      <Link href="/patients" className="back-link">
        ← Back to worklist
      </Link>
      <section className="page-header">
        <p className="eyebrow">Patient timeline</p>
        <h1>{patientName}</h1>
        <p className="lede">Escalation-aware detail for the selected patient.</p>
      </section>
      <EscalationEvidenceCard evidence={detail?.escalation_evidence ?? null} />
      <section className="section-card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Recent timeline</h2>
            <p className="section-subtitle">
              Showing {timeline.items.length} of {timeline.total} events
            </p>
          </div>
        </div>
        <TimelineList events={timeline.items} patientId={patientId} selectedEventId={selectedEventId} />
      </section>
    </main>
  );
}
