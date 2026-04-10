import StateNotice from "../../components/StateNotice";
import TimelineAppliedFilters from "../../components/patients/TimelineAppliedFilters";
import WorklistHeader from "../../components/patients/WorklistHeader";
import WorklistControls from "../../components/patients/WorklistControls";
import WorklistEmptyState from "../../components/patients/WorklistEmptyState";
import WorklistStateSummary from "../../components/patients/WorklistStateSummary";
import WorklistSummaryCard from "../../components/patients/WorklistSummaryCard";
import WorklistHighlights from "../../components/patients/WorklistHighlights";
import WorklistPaginationControls from "../../components/patients/WorklistPaginationControls";
import { fetchWorklistSummary } from "../../lib/api";
import { requireAuth } from "../../lib/auth/session";
import { pluralize } from "../../lib/format";
import { FILTER_LABELS } from "../../lib/statusLabels";
import {
  compareWorkflowStatuses,
  inferWorkflowStatusSummary,
} from "../../lib/workflowStatus";
import type { PatientTimelineWorklistSummaryItem } from "../../types/patient";

type WorklistResponse = Awaited<ReturnType<typeof fetchWorklistSummary>>;

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

const isRedirectLikeError = (error: unknown): boolean => {
  if (!error || typeof error !== "object") {
    return false;
  }
  const maybeError = error as { message?: unknown; digest?: unknown };
  if (maybeError.message === "NEXT_REDIRECT") {
    return true;
  }
  return typeof maybeError.digest === "string" && maybeError.digest.startsWith("NEXT_REDIRECT");
};

const normalizeArrayParam = (value?: string | string[]): string[] => {
  if (!value) {
    return [];
  }
  const arrayValue = Array.isArray(value) ? value : [value];
  return arrayValue
    .flatMap((entry) => entry.split(","))
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
};

const getFirstParam = (value?: string | string[]): string | undefined => {
  if (!value) {
    return undefined;
  }
  return Array.isArray(value) ? value[0] : value;
};

const parseBooleanParam = (value?: string | string[], defaultValue = false): boolean => {
  const raw = getFirstParam(value);
  if (raw === undefined) {
    return defaultValue;
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

const toHref = (params: URLSearchParams) => {
  const query = params.toString();
  return query ? `/patients?${query}` : "/patients";
};

const resolveWorkflowStatus = (item: PatientTimelineWorklistSummaryItem) =>
  item.workflow_status ?? inferWorkflowStatusSummary(item);

const getLatestEvidenceTimestamp = (item: PatientTimelineWorklistSummaryItem): string | null => {
  const taskSummary = item.task_summary ?? null;
  return (
    taskSummary?.latest_active_task_due_at ??
    taskSummary?.latest_active_task_created_at ??
    item.latest_event_occurred_at ??
    item.latest_unread_event_occurred_at ??
    item.oldest_unread_event_occurred_at ??
    null
  );
};

const compareWorklistItems = (
  a: PatientTimelineWorklistSummaryItem,
  b: PatientTimelineWorklistSummaryItem,
) => {
  const statusComparison = compareWorkflowStatuses(resolveWorkflowStatus(a), resolveWorkflowStatus(b));
  if (statusComparison !== 0) {
    return statusComparison;
  }

  const unreadA = a.has_unread_events ? a.unread_count : 0;
  const unreadB = b.has_unread_events ? b.unread_count : 0;
  if (unreadA !== unreadB) {
    return unreadB - unreadA;
  }

  const timestampA = getLatestEvidenceTimestamp(a);
  const timestampB = getLatestEvidenceTimestamp(b);
  if (timestampA && timestampB) {
    if (timestampA > timestampB) {
      return -1;
    }
    if (timestampA < timestampB) {
      return 1;
    }
  } else if (timestampA) {
    return -1;
  } else if (timestampB) {
    return 1;
  }

  return a.patient_display_name.localeCompare(b.patient_display_name);
};

export default async function PatientsPage({ searchParams }: PageProps) {
  const resolvedSearchParams =
    (searchParams ? await searchParams : {}) as Record<string, string | string[] | undefined>;

  const queueParams = createSearchParams(resolvedSearchParams);
  const queueQueryString = queueParams.toString();
  const retryHref = queueQueryString ? `/patients?${queueQueryString}` : "/patients";
  await requireAuth(retryHref);

  const hasUnreadOnly = parseBooleanParam(resolvedSearchParams.has_unread_events, false);
  const activeOnly = parseBooleanParam(resolvedSearchParams.active_only, true);
  const patientIds = normalizeArrayParam(resolvedSearchParams.patient_ids);
  const limitParam = getFirstParam(resolvedSearchParams.limit);
  const skipParam = getFirstParam(resolvedSearchParams.skip);
  const parsedLimit = limitParam ? Number.parseInt(limitParam, 10) : NaN;
  const pageSize = Number.isFinite(parsedLimit) ? Math.min(Math.max(parsedLimit, 1), 100) : 25;
  const parsedSkip = skipParam ? Number.parseInt(skipParam, 10) : NaN;
  const skip = Number.isFinite(parsedSkip) && parsedSkip > 0 ? parsedSkip : 0;

  const hasActiveFilters = hasUnreadOnly || patientIds.length > 0 || activeOnly === false;

  const buildFilterHref = (removals: Array<{ key: string; value?: string | null }>) => {
    const params = createSearchParams(resolvedSearchParams);
    removals.forEach((removal) => removeParamValue(params, removal.key, removal.value));
    params.delete("skip");
    return toHref(params);
  };

  const buildPatientFilterHref = (patientIdToRemove: string) => {
    const params = createSearchParams(resolvedSearchParams, ["patient_ids"]);
    patientIds
      .filter((patientId) => patientId !== patientIdToRemove)
      .forEach((patientId) => params.append("patient_ids", patientId));
    params.delete("skip");
    return toHref(params);
  };

  const clearFiltersHref = hasActiveFilters
    ? (() => {
        const params = createSearchParams(resolvedSearchParams, [
          "has_unread_events",
          "patient_ids",
          "active_only",
        ]);
        params.delete("skip");
        return toHref(params);
      })()
    : null;

  const preservedParams: Record<string, string | string[]> = {};
  if (limitParam && !Number.isNaN(parsedLimit) && parsedLimit !== 25) {
    preservedParams.limit = limitParam;
  }

  let worklist: WorklistResponse | null = null;
  try {
    worklist = await fetchWorklistSummary(
      {
        limit: pageSize,
        skip,
        activeOnly,
        ...(patientIds.length ? { patientIds } : {}),
        ...(hasUnreadOnly ? { hasUnreadEvents: true } : {}),
      },
      { authRedirectPath: retryHref },
    );
  } catch (error) {
    if (isRedirectLikeError(error)) {
      throw error;
    }
    console.error("Failed to load patient worklist", error);
    const headerTitle = "Patient queue";
    const headerSubtitle = hasActiveFilters ? "Filtered queue view" : "Standard queue view";
    const headerDescription = hasActiveFilters
      ? "You are viewing a narrowed queue slice. Filters and chips show what is in effect."
      : "Escalation-aware queue showing patients who currently need intervention work.";
    const headerChips: Array<{ id: string; label: string }> = [
      { id: "scope-mode", label: activeOnly ? "Standard queue view" : "All patients view" },
      ...(hasUnreadOnly ? [{ id: "scope-unread", label: FILTER_LABELS.unreadOnly }] : []),
      ...patientIds.map((patientId) => ({ id: `patient-${patientId}`, label: `Patient ${patientId}` })),
    ];

    return (
      <main className="page">
        <WorklistHeader
          title={headerTitle}
          subtitle={headerSubtitle}
          description={headerDescription}
          chips={headerChips}
        />
        <StateNotice
          tone="danger"
          title="Unable to load the patient queue"
          body="The backend request failed. Retry or check that the backend service is healthy."
          actions={[{ label: "Retry", href: retryHref }]}
        />
      </main>
    );
  }

  if (!worklist) {
    return null;
  }

  const queueItems = [...worklist.items].sort(compareWorklistItems);
  const visibleCount = queueItems.length;
  const totalCount = worklist.total;
  const viewDescriptor = activeOnly ? "Standard queue view" : "All patients view";
  const filterDescriptors: string[] = [viewDescriptor];

  if (hasUnreadOnly) {
    filterDescriptors.push(FILTER_LABELS.unreadOnly);
  }
  if (patientIds.length === 1) {
    filterDescriptors.push(`Patient ${patientIds[0]}`);
  } else if (patientIds.length > 1) {
    filterDescriptors.push(`${patientIds.length} patients selected`);
  }

  const detailParts = [filterDescriptors.join(" • "), `${totalCount} total recorded`];
  if (!hasActiveFilters && totalCount <= 3) {
    detailParts.push("Queue is currently quiet");
  }

  const statePrimary = `Showing ${pluralize(visibleCount, "patient")}${
    totalCount > visibleCount || pageSize !== 25 ? ` (limit ${pageSize})` : ""
  }`;
  const stateDetail = detailParts.filter(Boolean).join(" • ");

  const headerTitle = "Patient queue";
  const headerSubtitle = hasActiveFilters ? "Filtered queue view" : "Standard queue view";
  const headerDescription = hasActiveFilters
    ? "You are viewing a narrowed queue slice. Filters and chips show what is in effect."
    : "Escalation-aware queue showing patients who currently need intervention work.";
  const headerChips: Array<{ id: string; label: string }> = [];
  headerChips.push({
    id: "scope-mode",
    label: activeOnly ? "Standard queue view" : "All patients view",
  });
  if (hasUnreadOnly) {
    headerChips.push({ id: "scope-unread", label: FILTER_LABELS.unreadOnly });
  }
  if (patientIds.length === 1) {
    headerChips.push({ id: "scope-single", label: `Patient ${patientIds[0]}` });
  } else if (patientIds.length > 1) {
    headerChips.push({ id: "scope-multi", label: `${patientIds.length} patients selected` });
  }

  const resultsHelper = visibleCount
    ? "Cards below mirror the queue slice above."
    : hasActiveFilters
      ? "No patients match the current filters."
      : "Queue is quiet right now.";

  return (
    <main className="page">
      <WorklistHeader
        title={headerTitle}
        subtitle={headerSubtitle}
        description={headerDescription}
        chips={headerChips}
      />
      <WorklistControls
        activeOnly={activeOnly}
        hasUnreadOnly={hasUnreadOnly}
        patientIdsText={patientIds.join(", ")}
        preservedParams={preservedParams}
      />
      <section className="worklist-context" aria-label="Queue review">
        <WorklistStateSummary
          primary={statePrimary}
          detail={stateDetail}
          helper="Totals, filters, and window controls reflect this queue slice."
        />
        {hasActiveFilters ? (
          <TimelineAppliedFilters
            chips={[
              ...(hasUnreadOnly
                ? [
                    {
                      id: "unread-only",
                      label: FILTER_LABELS.unreadOnly,
                      href: buildFilterHref([{ key: "has_unread_events" }]),
                    },
                  ]
                : []),
              ...(!activeOnly
                ? [
                    {
                      id: "queue-mode",
                      label: "All patients view",
                      href: buildFilterHref([{ key: "active_only" }]),
                    },
                  ]
                : []),
              ...patientIds.map((patientId) => ({
                id: `patient:${patientId}`,
                label: `Patient ${patientId}`,
                href: buildPatientFilterHref(patientId),
              })),
            ]}
            clearHref={clearFiltersHref}
          />
        ) : null}
        {visibleCount > 0 ? (
          <>
            <WorklistHighlights
              items={queueItems}
              helper="Counts reflect patients currently visible."
            />
            <WorklistPaginationControls
              total={totalCount}
              visibleCount={visibleCount}
              limit={pageSize}
              skip={skip}
              searchParams={resolvedSearchParams}
            />
          </>
        ) : null}
      </section>
      {visibleCount === 0 ? (
        <section className="worklist-results" aria-label="Patient queue review">
          <div className="worklist-results-head">
            <p className="worklist-context-label">Patient review</p>
            <p className="worklist-context-helper">
              Queue view: {activeOnly ? "Standard" : "All patients"} · {resultsHelper}
            </p>
          </div>
          <WorklistEmptyState hasFilters={hasActiveFilters} clearHref={clearFiltersHref} />
        </section>
      ) : (
        <section className="worklist-results" aria-label="Patient queue review">
          <div className="worklist-results-head">
            <p className="worklist-context-label">Patient review</p>
            <p className="worklist-context-helper">
              Queue view: {activeOnly ? "Standard" : "All patients"} · {resultsHelper}
            </p>
          </div>
          <div className="worklist-grid" role="list">
            {queueItems.map((item) => (
              <WorklistSummaryCard
                key={item.patient_id}
                summary={item}
                queueQueryString={queueQueryString}
              />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
