import Link from "next/link";
import { revalidatePath } from "next/cache";

import StateNotice from "../../../components/StateNotice";
import CreateTaskForm, { TaskFormValues } from "../../../components/patients/CreateTaskForm";
import EscalationActionBar, {
  EscalationActionRequest,
} from "../../../components/patients/EscalationActionBar";
import EscalationEvidenceCard from "../../../components/patients/EscalationEvidenceCard";
import PatientEvidenceSummary from "../../../components/patients/PatientEvidenceSummary";
import PatientRecentActivityStrip from "../../../components/patients/PatientRecentActivityStrip";
import PatientWorkflowHeader from "../../../components/patients/PatientWorkflowHeader";
import TimelineAppliedFilters from "../../../components/patients/TimelineAppliedFilters";
import TimelineFilters from "../../../components/patients/TimelineFilters";
import TimelineList from "../../../components/patients/TimelineList";
import TimelinePaginationControls from "../../../components/patients/TimelinePaginationControls";
import TimelineEventDetail from "../../../components/patients/TimelineEventDetail";
import TimelineStateSummary from "../../../components/patients/TimelineStateSummary";
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
import { formatDueDate, formatEventType, pluralize } from "../../../lib/format";
import { requireAuth } from "../../../lib/auth/session";
import STATUS_LABELS, { FILTER_LABELS } from "../../../lib/statusLabels";
import type { EscalationStatus, PatientEscalation } from "../../../types/patient";

type WorklistSummaryResponse = Awaited<ReturnType<typeof fetchWorklistSummary>>;
type TimelineResponse = Awaited<ReturnType<typeof fetchPatientTimeline>>;

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export const dynamic = "force-dynamic";

const normalizeArrayParam = (value?: string | string[]): string[] => {
  if (!value) {
    return [];
  }
  const arrayValue = Array.isArray(value) ? value : [value];
  return arrayValue.map((entry) => entry.trim()).filter((entry) => entry.length > 0);
};

const getFirstParam = (value?: string | string[]): string | undefined => {
  if (!value) {
    return undefined;
  }
  return Array.isArray(value) ? value[0] : value;
};

const parseBooleanParam = (value?: string | string[]): boolean => {
  const raw = getFirstParam(value);
  if (!raw) {
    return false;
  }
  const normalized = raw.toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "on";
};

const createSearchParams = (
  source: Record<string, string | string[] | undefined>,
  omitKeys: string[] = [],
): URLSearchParams => {
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

const removeParamValue = (params: URLSearchParams, key: string, value?: string | null) => {
  if (value === undefined || value === null) {
    params.delete(key);
    return;
  }
  const remaining = params.getAll(key).filter((entry) => entry !== value);
  params.delete(key);
  remaining.forEach((entry) => params.append(key, entry));
};

export default async function PatientDetailPage({ params, searchParams }: PageProps) {
  const { id: patientId } = await params;
  const resolvedSearchParams =
    (searchParams ? await searchParams : {}) as Record<string, string | string[] | undefined>;
  const queueReturnQuery = getFirstParam(resolvedSearchParams?.queue_query);
  const queueReturnParams = queueReturnQuery ? new URLSearchParams(queueReturnQuery) : null;
  const queueViewActiveOnlyParam = queueReturnParams?.get("active_only");
  const queueViewActiveOnly =
    queueViewActiveOnlyParam === null || queueViewActiveOnlyParam === undefined
      ? true
      : queueViewActiveOnlyParam !== "0" &&
        queueViewActiveOnlyParam.toLowerCase() !== "false" &&
        queueViewActiveOnlyParam !== "off";
  const queueViewName = queueViewActiveOnly ? "Standard queue view" : "All patients view";
  const queueReturnHref =
    queueReturnQuery && queueReturnQuery.length > 0 ? `/patients?${queueReturnQuery}` : "/patients";
  const queueReturnLabel = queueReturnQuery
    ? `← Return to ${queueViewName.toLowerCase()}`
    : "← Back to worklist";
  const hasQueueReturnContext = Boolean(queueReturnQuery);
  const requestedEventParam = resolvedSearchParams?.eventId;
  const requestedEventId = getFirstParam(requestedEventParam);
  const eventTypeFilters = normalizeArrayParam(resolvedSearchParams?.event_types);
  const includeOnlyOpenWork = parseBooleanParam(resolvedSearchParams?.include_only_open_work);
  const relatedEscalationFilter = getFirstParam(resolvedSearchParams?.related_escalation_id);
  const cursorOccurredAt = getFirstParam(resolvedSearchParams?.cursor_occurred_at);
  const cursorEventId = getFirstParam(resolvedSearchParams?.cursor_event_id);
  const cursorDirection = getFirstParam(resolvedSearchParams?.cursor_direction);
  const limitParam = getFirstParam(resolvedSearchParams?.limit);
  const parsedLimit = limitParam ? Number.parseInt(limitParam, 10) : NaN;
  const pageSize = Number.isFinite(parsedLimit) ? Math.min(Math.max(parsedLimit, 5), 100) : 25;
  const pagePath = `/patients/${patientId}`;
  const originalSearchParams = createSearchParams(resolvedSearchParams);
  const originalQueryString = originalSearchParams.toString();
  const detailRetryHref = originalQueryString ? `${pagePath}?${originalQueryString}` : pagePath;
  requireAuth(detailRetryHref);

  const buildFilterHref = (
    removals: Array<{ key: string; value?: string | null }> = [],
  ): string => {
    const params = new URLSearchParams(originalQueryString);
    removals.forEach((removal) => removeParamValue(params, removal.key, removal.value));
    const query = params.toString();
    return query ? `${pagePath}?${query}` : pagePath;
  };

  const timelineFilters = {
    ...(eventTypeFilters.length ? { event_types: eventTypeFilters } : {}),
    ...(relatedEscalationFilter ? { related_escalation_id: relatedEscalationFilter } : {}),
    ...(includeOnlyOpenWork ? { include_only_open_work: true } : {}),
  };

  const requestFilters = { ...timelineFilters };
  if (cursorDirection === "newer" && cursorOccurredAt) {
    requestFilters.occurred_after = cursorOccurredAt;
  }
  const hasRequestFilters = Object.keys(requestFilters).length > 0;

  const baseQueryParams = createSearchParams(resolvedSearchParams, ["eventId"]);
  const baseQueryString = baseQueryParams.toString();
  const resetPaginationParams = createSearchParams(resolvedSearchParams, [
    "eventId",
    "cursor_occurred_at",
    "cursor_event_id",
    "cursor_direction",
  ]);
  const resetPaginationQueryString = resetPaginationParams.toString();
  const isPaged = Boolean(cursorOccurredAt || cursorEventId);

  let worklist: WorklistSummaryResponse | null = null;
  let timeline: TimelineResponse | null = null;
  try {
    [worklist, timeline] = await Promise.all([
      fetchWorklistSummary({ patientIds: [patientId], limit: 1 }, { authRedirectPath: detailRetryHref }),
      fetchPatientTimeline(
        patientId,
        {
          limit: pageSize,
          ...(cursorDirection === "newer"
            ? {}
            : {
                cursorOccurredAt: cursorOccurredAt ?? undefined,
                cursorEventId: cursorEventId ?? undefined,
              }),
          filters: hasRequestFilters ? requestFilters : undefined,
        },
        { authRedirectPath: detailRetryHref },
      ),
    ]);
  } catch (error) {
    console.error(`Failed to load timeline for patient ${patientId}`, error);
    return (
      <main className="page">
        <Link href={queueReturnHref} className="back-link">
          {queueReturnLabel}
        </Link>
        <StateNotice
          tone="danger"
          title="Unable to load patient evidence"
          body="The patient timeline could not be loaded. Retry or return to the worklist."
          actions={[
            { label: "Retry", href: detailRetryHref },
            { label: "Back to queue", href: queueReturnHref, variant: "secondary" },
          ]}
        />
      </main>
    );
  }

  if (!worklist || !timeline) {
    return null;
  }

  const latestTimelineEvent = timeline.items[0] ?? null;
  const selectedEventId = requestedEventId ?? latestTimelineEvent?.event_id;
  let detailLoadFailed = false;
  const detail = selectedEventId
    ? await fetchPatientTimelineEvent(patientId, selectedEventId, {
        authRedirectPath: detailRetryHref,
      }).catch((error) => {
        detailLoadFailed = true;
        console.error(`Failed to load timeline event ${selectedEventId} for patient ${patientId}`, error);
        return null;
      })
    : null;
  const selectedEventTitleId = selectedEventId ? `timeline-${selectedEventId}-title` : null;
  const worklistSummary = worklist.items[0] ?? null;
  const patientName = worklistSummary?.patient_display_name ?? detail?.item.patient_id ?? patientId;
  const escalationIdFromDetail = detail?.item.related_escalation_id;
  const escalationIdFromEvidence =
    detail?.escalation_evidence?.latest_open_escalation_id ??
    worklistSummary?.latest_open_escalation_id ??
    null;
  const activeEscalationId = escalationIdFromDetail ?? escalationIdFromEvidence ?? null;
  const escalationEvidence = detail?.escalation_evidence ?? null;
  const taskSummary = detail?.task_summary ?? worklistSummary?.task_summary ?? null;
  const workflowStatus = detail?.workflow_status ?? worklistSummary?.workflow_status ?? null;

  let activeEscalation: PatientEscalation | null = null;
  if (activeEscalationId) {
    try {
      activeEscalation = await fetchEscalation(activeEscalationId, { authRedirectPath: detailRetryHref });
    } catch (error) {
      console.error("Unable to load escalation context", error);
      activeEscalation = null;
    }
  }

  const escalationStatus: EscalationStatus | null =
    activeEscalation?.status ?? escalationEvidence?.latest_open_escalation_status ?? null;
  const createTaskContextLabel = activeEscalation
    ? `${activeEscalation.escalation_type} · ${activeEscalation.severity}${
        activeEscalation.sla_due_at ? ` · SLA ${formatDueDate(activeEscalation.sla_due_at)}` : ""
      }`
    : undefined;
  const appliedFilterChips: { id: string; label: string; href: string }[] = [];

  eventTypeFilters.forEach((eventType) => {
    appliedFilterChips.push({
      id: `event_type:${eventType}`,
      label: formatEventType(eventType),
      href: buildFilterHref([{ key: "event_types", value: eventType }]),
    });
  });

  if (includeOnlyOpenWork) {
    appliedFilterChips.push({
      id: "include_only_open_work",
      label: FILTER_LABELS.openWorkOnly,
      href: buildFilterHref([{ key: "include_only_open_work" }]),
    });
  }

  if (relatedEscalationFilter) {
    appliedFilterChips.push({
      id: "related_escalation_id",
      label:
        activeEscalationId && relatedEscalationFilter === activeEscalationId
          ? FILTER_LABELS.activeEscalationOnly
          : STATUS_LABELS.linkedEscalation,
      href: buildFilterHref([{ key: "related_escalation_id" }]),
    });
  }

  const hasActiveTimelineFilters = appliedFilterChips.length > 0;
  const clearAllFiltersHref = hasActiveTimelineFilters
    ? buildFilterHref([
        { key: "event_types" },
        { key: "include_only_open_work" },
        { key: "related_escalation_id" },
      ])
    : null;
  const patientTotalEvents =
    typeof worklistSummary?.total_events === "number" ? worklistSummary.total_events : null;
  const patientHasAnyTimelineEvidence =
    patientTotalEvents !== null
      ? patientTotalEvents > 0
      : timeline.total > 0 || timeline.items.length > 0;
  const visibleCount = timeline.items.length;
  const timelinePrimarySummary = `Showing ${pluralize(
    visibleCount,
    "timeline event",
  )} (limit ${timeline.limit})`;
  const filterDescriptors: string[] = [];
  if (includeOnlyOpenWork) {
    filterDescriptors.push(STATUS_LABELS.openWork);
  }
  if (relatedEscalationFilter) {
    filterDescriptors.push(STATUS_LABELS.linkedEscalation);
  }
  if (eventTypeFilters.length) {
    filterDescriptors.push(
      eventTypeFilters.length === 1
        ? formatEventType(eventTypeFilters[0])
        : `${eventTypeFilters.length} event types`,
    );
  }
  const detailParts: string[] = [];
  if (filterDescriptors.length) {
    detailParts.push(`Filters: ${filterDescriptors.join(" · ")}`);
  }
  detailParts.push(
    isPaged
      ? cursorDirection === "newer"
        ? "Viewing newer page"
        : "Viewing older page"
      : "Viewing latest events",
  );
  detailParts.push(`${timeline.total} total recorded`);
  const timelineEvidenceCount = patientTotalEvents ?? timeline.total;
  const isSparseTimeline =
    patientHasAnyTimelineEvidence && timelineEvidenceCount > 0 && timelineEvidenceCount <= 3;
  if (isSparseTimeline) {
    detailParts.push("Limited evidence so far");
  }
  const timelineDetailSummary = detailParts.filter(Boolean).join(" • ");
  const queueFilterSummary =
    hasActiveTimelineFilters && filterDescriptors.length
      ? filterDescriptors.join(" • ")
      : null;
  const arrivalContextHelper = hasActiveTimelineFilters
    ? queueFilterSummary
      ? `${queueViewName} · ${queueFilterSummary}`
      : `${queueViewName} · Filters in effect`
    : queueReturnQuery
      ? `${queueViewName} · No filters from queue`
      : null;
  const detailEmptyHints: string[] = [];
  if (detailLoadFailed) {
    detailEmptyHints.push("Event detail failed to load. Retry or refresh the page.");
  }
  if (hasActiveTimelineFilters) {
    detailEmptyHints.push("Filters active");
  }
  if (isPaged) {
    detailEmptyHints.push(cursorDirection === "newer" ? "Viewing newer page" : "Viewing older page");
  }
  if (!timeline.items.length) {
    detailEmptyHints.push("No events on this page");
  }

  const escalationAction = async (
    request: EscalationActionRequest,
  ): Promise<{ success: boolean; message?: string }> => {
    "use server";

    if (!activeEscalationId) {
      return { success: false, message: "No escalation is available for this patient." };
    }

    try {
      if (request.type === "acknowledge") {
        await acknowledgeEscalation(activeEscalationId, { authRedirectPath: detailRetryHref });
      } else if (request.type === "start") {
        await updateEscalationStatus(
          activeEscalationId,
          {
            status: "in_progress",
            note: request.note ?? null,
          },
          { authRedirectPath: detailRetryHref },
        );
      } else if (request.type === "resolve") {
        await resolveEscalation(
          activeEscalationId,
          {
            resolution_notes: request.note ?? null,
          },
          { authRedirectPath: detailRetryHref },
        );
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
      await createInterventionTask(
        activeEscalationId,
        {
          title: payload.title,
          description: payload.description ?? null,
          priority: payload.priority,
          due_at: dueAtIso,
        },
        { authRedirectPath: detailRetryHref },
      );
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
      <Link href={queueReturnHref} className="back-link">
        {queueReturnLabel}
      </Link>
      <div className="patient-workflow-overview">
        <PatientWorkflowHeader
          patientName={patientName}
          patientId={patientId}
          summary={worklistSummary}
          evidence={escalationEvidence}
          taskSummary={taskSummary}
          workflowStatus={workflowStatus}
          queueViewName={queueViewName}
          queueFilterSummary={queueFilterSummary}
          hasQueueReturnContext={hasQueueReturnContext}
          latestEvent={latestTimelineEvent}
          activeEscalationStatus={escalationStatus}
        />
        <PatientRecentActivityStrip latestEvent={latestTimelineEvent} summary={worklistSummary} />
      </div>
      <PatientEvidenceSummary evidence={escalationEvidence} summary={worklistSummary} />
      <EscalationEvidenceCard evidence={escalationEvidence} />
      <section className="section-card">
        <div className="section-header">
          <div>
            <p className="eyebrow">Escalation actions</p>
            <h2 className="section-title">Current escalation</h2>
            <p className="section-subtitle">Act on the escalation and capture intervention work.</p>
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
            <p className="eyebrow">Timeline evidence</p>
            <h2 className="section-title">Evidence review</h2>
            <p className="section-subtitle">Use filters, pagination, and detail drill-ins to review evidence.</p>
          </div>
        </div>
        <TimelineFilters
          patientId={patientId}
          eventTypes={eventTypeFilters}
          includeOnlyOpenWork={includeOnlyOpenWork}
          relatedEscalationId={relatedEscalationFilter ?? null}
          activeEscalationId={activeEscalationId}
          pageSize={pageSize}
        />
        <TimelineAppliedFilters chips={appliedFilterChips} clearHref={clearAllFiltersHref} />
        {arrivalContextHelper ? (
          <div className="timeline-arrival-context">
            <p className="worklist-context-label">{queueViewName}</p>
            <p className="timeline-arrival-context-body">{arrivalContextHelper}</p>
          </div>
        ) : null}
        <TimelineStateSummary
          primary={timelinePrimarySummary}
          detail={timelineDetailSummary}
        />
        <TimelinePaginationControls
          patientId={patientId}
          total={timeline.total}
          visibleCount={timeline.items.length}
          limit={timeline.limit}
          hasMore={timeline.has_more}
          nextCursorOccurredAt={timeline.next_cursor_occurred_at}
          nextCursorEventId={timeline.next_cursor_event_id}
          resetQueryString={resetPaginationQueryString}
          isPaged={isPaged}
        />
        <TimelineList
          events={timeline.items}
          patientId={patientId}
          selectedEventId={selectedEventId}
          baseQueryString={baseQueryString}
          hasAnyEvents={patientHasAnyTimelineEvidence}
          isFiltered={hasActiveTimelineFilters}
          clearFiltersHref={clearAllFiltersHref}
        />
      </section>
      <TimelineEventDetail
        event={detail?.item ?? null}
        selectedRowLabelId={selectedEventTitleId}
        contextSummary={timelineDetailSummary}
        emptyHints={detailEmptyHints}
        hasVisibleTimelineEvents={timeline.items.length > 0}
        hasActiveFilters={hasActiveTimelineFilters}
      />
    </main>
  );
}
