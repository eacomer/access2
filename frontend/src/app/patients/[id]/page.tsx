import Link from "next/link";
import { revalidatePath } from "next/cache";

import CreateTaskForm, { TaskFormValues } from "../../../components/patients/CreateTaskForm";
import EscalationActionBar, { EscalationActionRequest } from "../../../components/patients/EscalationActionBar";
import EscalationEvidenceCard from "../../../components/patients/EscalationEvidenceCard";
import TimelineList from "../../../components/patients/TimelineList";
import {
  acknowledgeEscalation,
  createInterventionTask,
  fetchEscalation,
  fetchPatientTimeline,
  fetchPatientTimelineEvent,
  fetchWorklistSummary,
  resolveEscalation,
  updateEscalationStatus,
} from "../../../lib/api";
import { formatDueDate } from "../../../lib/format";
import type { EscalationStatus, PatientEscalation } from "../../../types/patient";

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
  const pagePath = `/patients/${patientId}`;

  const [worklist, timeline] = await Promise.all([
    fetchWorklistSummary({ patientIds: [patientId], limit: 1 }),
    fetchPatientTimeline(patientId, { limit: 25 }),
  ]);

  const selectedEventId = requestedEventId ?? timeline.items[0]?.event_id;
  const detail = selectedEventId
    ? await fetchPatientTimelineEvent(patientId, selectedEventId)
    : null;
  const patientName = worklist.items[0]?.patient_display_name ?? detail?.item.patient_id ?? patientId;
  const escalationIdFromDetail = detail?.item.related_escalation_id;
  const escalationIdFromEvidence =
    detail?.escalation_evidence?.latest_open_escalation_id ??
    worklist.items[0]?.latest_open_escalation_id ??
    null;
  const activeEscalationId = escalationIdFromDetail ?? escalationIdFromEvidence ?? null;

  let activeEscalation: PatientEscalation | null = null;
  if (activeEscalationId) {
    try {
      activeEscalation = await fetchEscalation(activeEscalationId);
    } catch (error) {
      console.error("Unable to load escalation context", error);
      activeEscalation = null;
    }
  }

  const escalationStatus: EscalationStatus | null =
    activeEscalation?.status ?? detail?.escalation_evidence?.latest_open_escalation_status ?? null;
  const createTaskContextLabel = activeEscalation
    ? `${activeEscalation.escalation_type} · ${activeEscalation.severity}${
        activeEscalation.sla_due_at ? ` · SLA ${formatDueDate(activeEscalation.sla_due_at)}` : ""
      }`
    : undefined;

  const escalationAction = async (
    request: EscalationActionRequest,
  ): Promise<{ success: boolean; message?: string }> => {
    "use server";

    if (!activeEscalationId) {
      return { success: false, message: "No escalation is available for this patient." };
    }

    try {
      if (request.type === "acknowledge") {
        await acknowledgeEscalation(activeEscalationId);
      } else if (request.type === "start") {
        await updateEscalationStatus(activeEscalationId, {
          status: "in_progress",
          note: request.note ?? null,
        });
      } else if (request.type === "resolve") {
        await resolveEscalation(activeEscalationId, {
          resolution_notes: request.note ?? null,
        });
      }
      revalidatePath(pagePath);
      const successMessage =
        request.type === "resolve"
          ? "Escalation resolved."
          : request.type === "start"
            ? "Escalation marked as in progress."
            : "Escalation acknowledged.";
      return { success: true, message: successMessage };
    } catch (error) {
      console.error("Failed to update escalation", error);
      return {
        success: false,
        message: error instanceof Error ? error.message : "Unable to update escalation.",
      };
    }
  };

  const submitTask = async (
    payload: TaskFormValues,
  ): Promise<{ success: boolean; message?: string }> => {
    "use server";

    if (!activeEscalationId) {
      return { success: false, message: "An active escalation is required to create a task." };
    }

    const dueAtIso = payload.dueAt ? new Date(payload.dueAt).toISOString() : null;

    try {
      await createInterventionTask(activeEscalationId, {
        title: payload.title,
        description: payload.description ?? null,
        priority: payload.priority,
        due_at: dueAtIso,
      });
      revalidatePath(pagePath);
      return { success: true, message: "Task created successfully." };
    } catch (error) {
      console.error("Failed to create task", error);
      return {
        success: false,
        message: error instanceof Error ? error.message : "Unable to create task.",
      };
    }
  };

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
            <p className="eyebrow">Queue actions</p>
            <h2 className="section-title">Escalation workflow</h2>
            <p className="section-subtitle">
              Act on the escalation and capture intervention work without leaving the queue.
            </p>
          </div>
        </div>
        <EscalationActionBar status={escalationStatus} onAction={escalationAction} />
        <CreateTaskForm
          patientName={patientName}
          contextLabel={createTaskContextLabel}
          disabled={!activeEscalationId}
          disabledMessage="Tasks are created when a patient has an open escalation."
          onCreate={submitTask}
        />
      </section>
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
