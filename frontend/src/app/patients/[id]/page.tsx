import Link from "next/link";
import { revalidatePath } from "next/cache";

import StateNotice from "../../../components/StateNotice";
import type { ActionResult } from "../../../components/patients/ActionFeedbackBanner";
import { TaskFormValues } from "../../../components/patients/CreateTaskForm";
import PatientActionControls from "../../../components/patients/PatientActionControls";
import { EscalationActionRequest } from "../../../components/patients/EscalationActionBar";
import EscalationEvidenceCard from "../../../components/patients/EscalationEvidenceCard";
import PatientEvidenceSummary from "../../../components/patients/PatientEvidenceSummary";
import PatientInterventionEvidenceSummary from "../../../components/patients/PatientInterventionEvidenceSummary";
import PatientRecentActivityStrip from "../../../components/patients/PatientRecentActivityStrip";
import PatientWorkflowHeader from "../../../components/patients/PatientWorkflowHeader";
import PatientWhyNowSummary from "../../../components/patients/PatientWhyNowSummary";
import { TaskActionRequest } from "../../../components/patients/TaskActionPanel";
import TimelineAppliedFilters from "../../../components/patients/TimelineAppliedFilters";
import TimelineFilters from "../../../components/patients/TimelineFilters";
import TimelineList from "../../../components/patients/TimelineList";
import TimelinePaginationControls from "../../../components/patients/TimelinePaginationControls";
import TimelineEventDetail from "../../../components/patients/TimelineEventDetail";
import TimelineStateSummary from "../../../components/patients/TimelineStateSummary";
import {
  acknowledgeEscalation,
  cancelInterventionTask,
  completeInterventionTask,
  createInterventionTask,
  fetchEscalation,
  fetchInterventionTask,
  fetchPatient,
  fetchPatientAuditStatus,
  fetchPatientBacklogDrillIn,
  fetchPatientTimeline,
  fetchPatientTimelineEvent,
  fetchWorklistSummary,
  resolveEscalation,
  startInterventionTask,
  updateEscalationStatus,
} from "../../../lib/api";
import { formatDateTime, formatDueDate, formatEventType, formatPriority, pluralize } from "../../../lib/format";
import { requireAuth } from "../../../lib/auth/session";
import STATUS_LABELS, { FILTER_LABELS } from "../../../lib/statusLabels";
import type {
  EscalationStatus,
  InterventionTask,
  PatientEscalation,
  PatientBacklogDrillInResponse,
  PatientTimelineDetailResponse,
  PatientTimelineFilters,
  PatientAuditStatus,
} from "../../../types/patient";

type WorklistSummaryResponse = Awaited<ReturnType<typeof fetchWorklistSummary>>;
type TimelineResponse = Awaited<ReturnType<typeof fetchPatientTimeline>>;
type PatientResponse = Awaited<ReturnType<typeof fetchPatient>>;
type ReviewPacketSnapshot = PatientBacklogDrillInResponse["snapshots"][number];
type WorklistSummaryItem = WorklistSummaryResponse["items"][number];
type EvidenceChainStatusTone = "positive" | "warning" | "critical" | "info";
type EvidenceChainRow = {
  label: string;
  status: string;
  tone: EvidenceChainStatusTone;
  explanation: string;
};

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

export const dynamic = "force-dynamic";

const revalidatePatientViews = ({
  pagePath,
  detailPath,
}: {
  pagePath: string;
  detailPath: string;
}) => {
  revalidatePath("/patients");
  revalidatePath(pagePath);
  if (detailPath !== pagePath) {
    revalidatePath(detailPath);
  }
};

const buildTaskResult = (task: InterventionTask | null): Pick<
  ActionResult,
  | "taskId"
  | "taskTitle"
  | "taskDescription"
  | "taskStatus"
  | "taskPriority"
  | "taskDueAt"
  | "taskCompletedAt"
  | "taskCompletedByUserId"
  | "taskCompletionNote"
  | "taskCreatedAt"
  | "taskUpdatedAt"
  | "taskPatientId"
  | "taskOrganizationId"
  | "taskEnrollmentId"
  | "taskEscalationId"
  | "taskAssignedUserId"
  | "taskCreatedByUserId"
> => ({
  taskId: task?.id ?? null,
  taskTitle: task?.title ?? null,
  taskDescription: task?.description ?? null,
  taskStatus: task?.status ?? null,
  taskPriority: task?.priority ?? null,
  taskDueAt: task?.due_at ?? null,
  taskCompletedAt: task?.completed_at ?? null,
  taskCompletedByUserId: task?.completed_by_user_id ?? null,
  taskCompletionNote: task?.completion_note ?? null,
  taskCreatedAt: task?.created_at ?? null,
  taskUpdatedAt: task?.updated_at ?? null,
  taskPatientId: task?.patient_id ?? null,
  taskOrganizationId: task?.organization_id ?? null,
  taskEnrollmentId: task?.enrollment_id ?? null,
  taskEscalationId: task?.escalation_id ?? null,
  taskAssignedUserId: task?.assigned_user_id ?? null,
  taskCreatedByUserId: task?.created_by_user_id ?? null,
});

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

const WORKFLOW_OUTCOME_MESSAGES: Record<string, string> = {
  task_started: "Task started successfully",
  task_completed: "Task completed successfully",
  task_created: "Task created successfully",
  escalation_started: "Escalation started successfully",
  escalation_resolved: "Escalation resolved successfully",
};

const formatBooleanLabel = (value: boolean) => (value ? "Yes" : "No");

const formatAuditList = (values: string[]) => (values.length > 0 ? values.join(", ") : "—");

const formatAuditStatusValue = (value?: string | null) =>
  value
    ? value
        .split("_")
        .filter(Boolean)
        .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
        .join(" ")
    : "—";

const AUDIT_BUNDLE_DOWNLOADS = [
  { format: "json", label: "Download JSON" },
  { format: "markdown", label: "Download Markdown" },
  { format: "pdf", label: "Download PDF" },
] as const;

const getAuditBundleUnavailableMessage = ({
  backlog,
  snapshot,
}: {
  backlog: PatientBacklogDrillInResponse;
  snapshot: ReviewPacketSnapshot;
}) => {
  if (snapshot.review_status === "rejected") {
    return "Unavailable for rejected snapshots.";
  }

  if (snapshot.review_status !== "approved") {
    return "Unavailable until approved.";
  }

  if (
    snapshot.id === backlog.audit_status.latest_snapshot_id &&
    !backlog.audit_status.audit_bundle.available
  ) {
    return "Approved snapshot is not export-ready.";
  }

  return null;
};

const getAuditBundleDownloadHref = ({
  snapshotId,
  format,
}: {
  snapshotId: string;
  format: (typeof AUDIT_BUNDLE_DOWNLOADS)[number]["format"];
}) => `/audit-bundles/${encodeURIComponent(snapshotId)}/${format}`;

const renderAuditStatusPanel = ({
  auditStatus,
  auditStatusLoadFailed,
  detailRetryHref,
}: {
  auditStatus: PatientAuditStatus | null;
  auditStatusLoadFailed: boolean;
  detailRetryHref: string;
}) => {
  if (auditStatusLoadFailed) {
    return (
      <StateNotice
        tone="warning"
        title="Audit status unavailable"
        body="The patient audit-status request failed. Other patient evidence remains available."
        actions={[{ label: "Retry", href: detailRetryHref }]}
      />
    );
  }

  if (!auditStatus) {
    return (
      <StateNotice
        tone="info"
        title="Audit status not loaded"
        body="Audit-status data is not available for this patient right now."
      />
    );
  }

  return (
    <div className="audit-readiness-table-wrap">
      <table className="audit-readiness-table">
        <tbody>
          <tr>
            <th scope="row">Has snapshot</th>
            <td>{formatBooleanLabel(auditStatus.has_snapshot)}</td>
          </tr>
          <tr>
            <th scope="row">Review state</th>
            <td>{formatAuditStatusValue(auditStatus.review_state?.state)}</td>
          </tr>
          <tr>
            <th scope="row">Review action</th>
            <td>
              {auditStatus.review_action ? (
                <>
                  <strong>{formatAuditStatusValue(auditStatus.review_action.action)}</strong>
                  <span> · {formatPriority(auditStatus.review_action.priority)}</span>
                  <p className="inline-helper">{auditStatus.review_action.reason}</p>
                </>
              ) : (
                "—"
              )}
            </td>
          </tr>
          <tr>
            <th scope="row">Audit bundle available</th>
            <td>{formatBooleanLabel(auditStatus.audit_bundle.available)}</td>
          </tr>
          <tr>
            <th scope="row">Audit bundle exported</th>
            <td>{formatBooleanLabel(auditStatus.audit_bundle.exported)}</td>
          </tr>
          <tr>
            <th scope="row">Export formats</th>
            <td>{formatAuditList(auditStatus.audit_bundle.export_formats)}</td>
          </tr>
          <tr>
            <th scope="row">Next step</th>
            <td>
              <strong>{formatAuditStatusValue(auditStatus.next_step.action)}</strong>
              <span> · {formatPriority(auditStatus.next_step.priority)}</span>
              <p className="inline-helper">{auditStatus.next_step.reason}</p>
            </td>
          </tr>
          <tr>
            <th scope="row">Completion summary</th>
            <td>
              <strong>{formatAuditStatusValue(auditStatus.completion_summary.status)}</strong>
              <p className="inline-helper">{auditStatus.completion_summary.reason}</p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

const renderOutcomeProofGapsPanel = ({
  auditStatus,
  auditStatusLoadFailed,
  patientBacklog,
  patientBacklogLoadFailed,
  worklistSummary,
  timeline,
  escalationEvidence,
  taskSummary,
  interventionEvidenceSummary,
}: {
  auditStatus: PatientAuditStatus | null;
  auditStatusLoadFailed: boolean;
  patientBacklog: PatientBacklogDrillInResponse | null;
  patientBacklogLoadFailed: boolean;
  worklistSummary: WorklistSummaryItem | null;
  timeline: TimelineResponse;
  escalationEvidence: PatientTimelineDetailResponse["escalation_evidence"] | null;
  taskSummary: PatientTimelineDetailResponse["task_summary"] | WorklistSummaryItem["task_summary"] | null;
  interventionEvidenceSummary: PatientTimelineDetailResponse["intervention_evidence_summary"] | null;
}) => {
  const totalEvents = worklistSummary?.total_events ?? timeline.total;
  const hasSignal = totalEvents > 0 || Boolean(worklistSummary?.attention_reason);
  const totalEscalations = interventionEvidenceSummary?.total_escalations ?? 0;
  const openEscalations =
    escalationEvidence?.open_escalation_count ?? worklistSummary?.open_escalation_count ?? 0;
  const hasEscalation = totalEscalations > 0 || openEscalations > 0 || Boolean(worklistSummary?.latest_open_escalation_id);
  const totalTasks =
    interventionEvidenceSummary?.total_tasks ??
    ((taskSummary?.open_task_count ?? 0) +
      (taskSummary?.in_progress_task_count ?? 0) +
      (taskSummary?.overdue_task_count ?? 0));
  const completedTasks = interventionEvidenceSummary?.completed_tasks ?? 0;
  const hasIntervention = totalTasks > 0 || completedTasks > 0;
  const hasOutcome =
    completedTasks > 0 ||
    interventionEvidenceSummary?.recent_completed_interventions.some((item) => Boolean(item.detail)) ||
    timeline.items.some((item) => item.related_outcome_id || item.event_type.toLowerCase().includes("outcome"));
  const latestSnapshot = patientBacklog?.snapshots.find(
    (snapshot) => snapshot.id === auditStatus?.latest_snapshot_id,
  );
  const hasSnapshot = auditStatus?.has_snapshot ?? Boolean(latestSnapshot);
  const hasRequiredEvidence = auditStatus?.completion_summary.has_required_evidence ?? false;
  const missingEvidenceCount = auditStatus?.completion_summary.missing_evidence_count ?? 0;
  const isRejected = auditStatus?.review_status === "rejected";
  const isOverrideApproval = Boolean(auditStatus?.review_state?.approval_override_used);
  const isApproved = auditStatus?.review_status === "approved";
  const bundleAvailable = auditStatus?.audit_bundle.available ?? false;
  const bundleExported = auditStatus?.audit_bundle.exported ?? false;

  const readinessSummary = auditStatusLoadFailed
    ? {
        title: "Proof gaps unavailable",
        body: "Audit-status data failed to load, so outcome proof gaps cannot be fully evaluated from the persisted review packet.",
        tone: "warning" as const,
      }
    : isRejected
      ? {
          title: "Proof packet rejected",
          body: "A persisted proof packet exists, but the latest review posture is rejected. No rejection controls are exposed here.",
          tone: "warning" as const,
        }
      : isOverrideApproval
        ? {
            title: "Approval depends on override review",
            body: "The proof packet is approved with override or superuser review. Override controls are not exposed in this read-only view.",
            tone: "info" as const,
          }
        : hasRequiredEvidence && isApproved && bundleAvailable
          ? {
              title: "Outcome proof supports audit readiness",
              body: bundleExported
                ? "Required proof elements are satisfied, review is approved, and an audit bundle export is recorded."
                : "Required proof elements are satisfied and review is approved; the audit bundle is available for export.",
              tone: "info" as const,
            }
          : {
              title: "Outcome proof gaps remain",
              body:
                auditStatus?.completion_summary.reason ??
                "The current patient data does not yet show every proof element needed for audit readiness.",
              tone: "warning" as const,
            };

  const rows: EvidenceChainRow[] = [
    {
      label: "Signal",
      status: hasSignal ? "Satisfied" : "Missing",
      tone: hasSignal ? "positive" : "critical",
      explanation: hasSignal
        ? worklistSummary?.attention_reason ?? `${totalEvents} timeline event(s) support why this patient required action.`
        : "No patient signal is visible from the current timeline or worklist summary.",
    },
    {
      label: "Escalation",
      status: hasEscalation ? "Satisfied" : "Missing",
      tone: hasEscalation ? "positive" : "critical",
      explanation: hasEscalation
        ? openEscalations > 0
          ? `${openEscalations} escalation(s) remain visible for audit context.`
          : "Escalation evidence is present in the intervention evidence summary."
        : "No escalation record is visible to connect the signal to action.",
    },
    {
      label: "Intervention",
      status: completedTasks > 0 ? "Satisfied" : hasIntervention ? "Partial" : "Missing",
      tone: completedTasks > 0 ? "positive" : hasIntervention ? "warning" : "critical",
      explanation:
        completedTasks > 0
          ? `${completedTasks} completed intervention task(s) are recorded.`
          : hasIntervention
            ? "Intervention work is present, but completion proof is not yet visible."
            : "No intervention task evidence is visible.",
    },
    {
      label: "Outcome",
      status: hasOutcome ? "Satisfied" : "Missing",
      tone: hasOutcome ? "positive" : "critical",
      explanation: hasOutcome
        ? "Outcome or completed-intervention evidence is visible for the patient."
        : "No measurable outcome evidence is visible yet.",
    },
    {
      label: "Evidence",
      status: auditStatusLoadFailed ? "Unknown" : hasRequiredEvidence ? "Satisfied" : "Missing",
      tone: auditStatusLoadFailed ? "info" : hasRequiredEvidence ? "positive" : "critical",
      explanation: auditStatusLoadFailed
        ? "Audit-status data failed to load."
        : missingEvidenceCount > 0
          ? `${missingEvidenceCount} required evidence item(s) are missing from the latest proof packet.`
          : auditStatus?.completion_summary.reason ?? "Required-evidence status is not available.",
    },
    {
      label: "Case Summary / Snapshot",
      status: hasSnapshot ? "Satisfied" : "Missing",
      tone: hasSnapshot ? "positive" : "critical",
      explanation: hasSnapshot
        ? `Persisted immutable snapshot is available${auditStatus?.latest_snapshot_id ? `: ${auditStatus.latest_snapshot_id}` : ""}.`
        : patientBacklogLoadFailed
          ? "Review-packet backlog failed to load, and no snapshot status is available."
          : "No immutable review packet snapshot exists yet.",
    },
    {
      label: "Review Posture",
      status: isRejected
        ? "Rejected"
        : isOverrideApproval
          ? "Override Approval"
          : isApproved
            ? "Satisfied"
            : auditStatus?.review_status
              ? formatAuditStatusValue(auditStatus.review_status)
              : "Missing",
      tone: isRejected ? "critical" : isApproved ? "positive" : auditStatus?.review_status ? "warning" : "critical",
      explanation:
        auditStatus?.review_state?.label ??
        auditStatus?.review_action?.reason ??
        "No review decision is visible yet.",
    },
    {
      label: "Audit Bundle",
      status: bundleExported ? "Exported" : bundleAvailable ? "Available" : "Not ready",
      tone: bundleExported ? "positive" : bundleAvailable ? "positive" : "warning",
      explanation: bundleExported
        ? `Successful export recorded${auditStatus?.audit_bundle.last_exported_at ? ` ${formatDateTime(auditStatus.audit_bundle.last_exported_at)}` : ""}.`
        : bundleAvailable
          ? `Audit bundle can be exported as ${formatAuditList(auditStatus?.audit_bundle.export_formats ?? [])}.`
          : "Audit bundle is not available until the proof packet is approved and export-ready.",
    },
  ];

  return (
    <>
      <StateNotice
        tone={readinessSummary.tone}
        title={readinessSummary.title}
        body={readinessSummary.body}
      />
      <div className="audit-readiness-table-wrap">
        <table className="audit-readiness-table">
          <thead>
            <tr>
              <th>Proof element</th>
              <th>Status</th>
              <th>Gap basis</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                <td>
                  <span className={`badge badge--${row.tone}`}>{row.status}</span>
                </td>
                <td>{row.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
};

const renderEvidenceChainPanel = ({
  auditStatus,
  auditStatusLoadFailed,
  patientBacklog,
  patientBacklogLoadFailed,
  worklistSummary,
  timeline,
  escalationEvidence,
  taskSummary,
  interventionEvidenceSummary,
}: {
  auditStatus: PatientAuditStatus | null;
  auditStatusLoadFailed: boolean;
  patientBacklog: PatientBacklogDrillInResponse | null;
  patientBacklogLoadFailed: boolean;
  worklistSummary: WorklistSummaryItem | null;
  timeline: TimelineResponse;
  escalationEvidence: PatientTimelineDetailResponse["escalation_evidence"] | null;
  taskSummary: PatientTimelineDetailResponse["task_summary"] | WorklistSummaryItem["task_summary"] | null;
  interventionEvidenceSummary: PatientTimelineDetailResponse["intervention_evidence_summary"] | null;
}) => {
  const totalEvents = worklistSummary?.total_events ?? timeline.total;
  const hasSignal = totalEvents > 0 || Boolean(worklistSummary?.attention_reason);
  const totalEscalations = interventionEvidenceSummary?.total_escalations ?? 0;
  const openEscalations =
    escalationEvidence?.open_escalation_count ?? worklistSummary?.open_escalation_count ?? 0;
  const hasEscalation = totalEscalations > 0 || openEscalations > 0 || Boolean(worklistSummary?.latest_open_escalation_id);
  const totalTasks =
    interventionEvidenceSummary?.total_tasks ??
    ((taskSummary?.open_task_count ?? 0) +
      (taskSummary?.in_progress_task_count ?? 0) +
      (taskSummary?.overdue_task_count ?? 0));
  const completedTasks = interventionEvidenceSummary?.completed_tasks ?? 0;
  const hasIntervention = totalTasks > 0 || completedTasks > 0;
  const hasOutcome =
    completedTasks > 0 ||
    interventionEvidenceSummary?.recent_completed_interventions.some((item) => Boolean(item.detail)) ||
    timeline.items.some((item) => item.related_outcome_id || item.event_type.toLowerCase().includes("outcome"));
  const latestSnapshot = patientBacklog?.snapshots.find(
    (snapshot) => snapshot.id === auditStatus?.latest_snapshot_id,
  );
  const hasSnapshot = auditStatus?.has_snapshot ?? Boolean(latestSnapshot);
  const hasCaseSummary = Boolean(latestSnapshot?.packet_json) || hasSnapshot;
  const hasRequiredEvidence = auditStatus?.completion_summary.has_required_evidence ?? false;
  const missingEvidenceCount = auditStatus?.completion_summary.missing_evidence_count ?? 0;

  const rows: EvidenceChainRow[] = [
    {
      label: "Signal",
      status: hasSignal ? "Present" : "Not yet available",
      tone: hasSignal ? "positive" : "info",
      explanation: hasSignal
        ? worklistSummary?.attention_reason ?? `${totalEvents} timeline event(s) available.`
        : "No timeline signal is available from the current patient data.",
    },
    {
      label: "Escalation",
      status: hasEscalation ? "Present" : "Not yet available",
      tone: hasEscalation ? "positive" : "info",
      explanation: hasEscalation
        ? openEscalations > 0
          ? `${openEscalations} open escalation(s) currently visible.`
          : "Escalation history is present in the intervention evidence summary."
        : "No escalation evidence is available from the current patient data.",
    },
    {
      label: "Intervention",
      status: completedTasks > 0 ? "Complete" : hasIntervention ? "Present" : "Not yet available",
      tone: completedTasks > 0 ? "positive" : hasIntervention ? "warning" : "info",
      explanation:
        completedTasks > 0
          ? `${completedTasks} completed intervention task(s) are recorded.`
          : hasIntervention
            ? "Intervention work exists but completion evidence is not yet visible."
            : "No intervention task evidence is available from the current patient data.",
    },
    {
      label: "Outcome",
      status: hasOutcome ? "Present" : "Not yet available",
      tone: hasOutcome ? "positive" : "info",
      explanation: hasOutcome
        ? "Outcome or completed-intervention evidence is visible in the current evidence set."
        : "No measurable outcome evidence is visible from the current patient data.",
    },
    {
      label: "Evidence",
      status: auditStatusLoadFailed
        ? "Not yet available"
        : hasRequiredEvidence
          ? "Complete"
          : missingEvidenceCount > 0
            ? "Missing"
            : "Not yet available",
      tone: auditStatusLoadFailed ? "info" : hasRequiredEvidence ? "positive" : "critical",
      explanation: auditStatusLoadFailed
        ? "Audit-status data failed to load; timeline evidence remains available below."
        : auditStatus?.completion_summary.reason ?? "Required-evidence status is not available.",
    },
    {
      label: "Case Summary",
      status: hasCaseSummary ? "Present" : "Not yet available",
      tone: hasCaseSummary ? "positive" : "info",
      explanation: hasCaseSummary
        ? "A persisted review packet snapshot is available to carry the case summary."
        : "No persisted review packet snapshot is available yet.",
    },
    {
      label: "Review Packet",
      status: hasSnapshot ? "Present" : "Not yet available",
      tone: hasSnapshot ? "positive" : "info",
      explanation: hasSnapshot
        ? `Latest snapshot: ${auditStatus?.latest_snapshot_id ?? latestSnapshot?.id ?? "available"}.`
        : "No immutable review packet snapshot is available for this patient.",
    },
    {
      label: "Review State",
      status:
        auditStatus?.review_status === "rejected"
          ? "Review rejected"
          : auditStatus?.review_state?.approval_override_used
            ? "Approved With Override"
            : auditStatus?.review_status === "approved"
              ? "Complete"
              : auditStatus?.review_status
                ? formatAuditStatusValue(auditStatus.review_status)
                : "Not yet available",
      tone:
        auditStatus?.review_status === "rejected"
          ? "critical"
          : auditStatus?.review_status === "approved"
            ? "positive"
            : auditStatus?.review_status
              ? "warning"
              : "info",
      explanation:
        auditStatus?.review_state?.label ??
        auditStatus?.review_action?.reason ??
        "No review decision state is available yet.",
    },
    {
      label: "Audit Bundle",
      status: auditStatus?.audit_bundle.exported
        ? "Complete"
        : auditStatus?.audit_bundle.available
          ? "Export available"
          : "Export not available",
      tone: auditStatus?.audit_bundle.exported
        ? "positive"
        : auditStatus?.audit_bundle.available
          ? "positive"
          : "warning",
      explanation: auditStatus?.audit_bundle.available
        ? auditStatus.audit_bundle.exported
          ? `Exported${auditStatus.audit_bundle.last_exported_at ? ` ${formatDateTime(auditStatus.audit_bundle.last_exported_at)}` : ""}.`
          : `Approved snapshot can be exported as ${formatAuditList(auditStatus.audit_bundle.export_formats)}.`
        : patientBacklogLoadFailed
          ? "Review-packet backlog failed to load; export posture may be incomplete."
          : "Audit bundle export is unavailable until the snapshot is approved and export-ready.",
    },
  ];

  return (
    <div className="audit-readiness-table-wrap">
      <table className="audit-readiness-table">
        <thead>
          <tr>
            <th>Step</th>
            <th>Status</th>
            <th>Evidence basis</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td>
                <span className={`badge badge--${row.tone}`}>{row.status}</span>
              </td>
              <td>{row.explanation}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const renderManifestVerificationPanel = ({
  auditStatus,
  auditStatusLoadFailed,
}: {
  auditStatus: PatientAuditStatus | null;
  auditStatusLoadFailed: boolean;
}) => {
  const hasSnapshot = auditStatus?.has_snapshot ?? false;
  const reviewStatus = auditStatus?.review_status ?? null;
  const isRejected = reviewStatus === "rejected";
  const isApproved = reviewStatus === "approved";
  const isOverrideApproval = Boolean(auditStatus?.review_state?.approval_override_used);
  const bundleAvailable = auditStatus?.audit_bundle.available ?? false;
  const bundleExported = auditStatus?.audit_bundle.exported ?? false;
  const hasFormats = Boolean(auditStatus?.audit_bundle.export_formats.length);

  const manifestVerificationStatus = auditStatusLoadFailed
    ? {
        status: "Not yet available",
        tone: "info" as const,
        explanation: "Audit-status data failed to load, so manifest verification posture is unavailable.",
      }
    : !hasSnapshot
      ? {
          status: "Verification unavailable",
          tone: "warning" as const,
          explanation: "No immutable review packet snapshot exists for this patient.",
        }
      : isRejected
        ? {
            status: "Verification unavailable",
            tone: "critical" as const,
            explanation: "The latest review packet was rejected, so audit bundle verification is unavailable.",
          }
        : !isApproved
          ? {
              status: "Verification unavailable",
              tone: "warning" as const,
              explanation: "Review packet approval is required before audit bundle verification is available.",
            }
          : !bundleAvailable
            ? {
                status: "Verification unavailable",
                tone: "warning" as const,
                explanation: "Audit bundle data is not available from the current persisted snapshot posture.",
              }
            : bundleExported
              ? {
                  status: "Verification-ready",
                  tone: "positive" as const,
                  explanation:
                    "Persisted audit bundle export is recorded; supplied manifests can be verified against persisted snapshot data.",
                }
              : {
                  status: "Verification supported",
                  tone: "positive" as const,
                  explanation:
                    "The approved snapshot is export-ready; the manifest payload is generated by audit bundle endpoints and is not exposed by this patient read endpoint.",
                };

  const rows: EvidenceChainRow[] = [
    {
      label: "Review Packet Snapshot",
      status: hasSnapshot ? "Present" : "Not yet available",
      tone: hasSnapshot ? "positive" : "info",
      explanation: hasSnapshot
        ? `Latest snapshot: ${auditStatus?.latest_snapshot_id ?? "available"}.`
        : "No immutable review packet snapshot is available for this patient.",
    },
    {
      label: "Review State",
      status: isRejected
        ? "Rejected"
        : isOverrideApproval
          ? "Approved With Override"
          : isApproved
            ? "Approved"
            : reviewStatus
              ? formatAuditStatusValue(reviewStatus)
              : "Not yet available",
      tone: isRejected ? "critical" : isApproved ? "positive" : reviewStatus ? "warning" : "info",
      explanation:
        auditStatus?.review_state?.label ??
        auditStatus?.review_action?.reason ??
        "No review decision state is available yet.",
    },
    {
      label: "Audit Bundle",
      status: bundleAvailable ? "Available" : "Unavailable",
      tone: bundleAvailable ? "positive" : "warning",
      explanation: bundleAvailable
        ? "Approved persisted snapshot can support audit bundle reads."
        : "Audit bundle is unavailable until the review packet is approved and export-ready.",
    },
    {
      label: "Export Status",
      status: bundleExported ? "Exported" : "Not exported",
      tone: bundleExported ? "positive" : bundleAvailable ? "warning" : "info",
      explanation: bundleExported
        ? `Last exported${auditStatus?.audit_bundle.last_exported_at ? ` ${formatDateTime(auditStatus.audit_bundle.last_exported_at)}` : ""}.`
        : bundleAvailable
          ? "Audit bundle is available, but no successful export event is recorded yet."
          : "Export is not available from the current review packet posture.",
    },
    {
      label: "Export Formats",
      status: hasFormats ? "Available" : "Not yet available",
      tone: hasFormats ? "positive" : "info",
      explanation: hasFormats
        ? formatAuditList(auditStatus?.audit_bundle.export_formats ?? [])
        : "No audit bundle export formats are exposed by the current patient audit status.",
    },
    {
      label: "Manifest Verification",
      ...manifestVerificationStatus,
    },
  ];

  return (
    <div className="audit-readiness-table-wrap">
      <table className="audit-readiness-table">
        <thead>
          <tr>
            <th>Check</th>
            <th>Status</th>
            <th>Verification basis</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td>
                <span className={`badge badge--${row.tone}`}>{row.status}</span>
              </td>
              <td>{row.explanation}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const sortSnapshotsByCreatedAtDesc = (snapshots: PatientBacklogDrillInResponse["snapshots"]) =>
  [...snapshots].sort((left, right) => {
    const createdComparison = right.created_at.localeCompare(left.created_at);
    return createdComparison !== 0 ? createdComparison : right.id.localeCompare(left.id);
  });

const renderPatientBacklogPanel = ({
  backlog,
  backlogLoadFailed,
  detailRetryHref,
}: {
  backlog: PatientBacklogDrillInResponse | null;
  backlogLoadFailed: boolean;
  detailRetryHref: string;
}) => {
  if (backlogLoadFailed) {
    return (
      <StateNotice
        tone="warning"
        title="Review packet backlog unavailable"
        body="The patient review-packet backlog request failed. Other patient evidence remains available."
        actions={[{ label: "Retry", href: detailRetryHref }]}
      />
    );
  }

  if (!backlog) {
    return (
      <StateNotice
        tone="info"
        title="Review packet backlog not loaded"
        body="Review-packet backlog data is not available for this patient right now."
      />
    );
  }

  const latestSnapshots = sortSnapshotsByCreatedAtDesc(backlog.snapshots).slice(0, 3);

  return (
    <>
      <div className="queue-impact-grid">
        <div className="queue-impact-stat">
          <span className="queue-impact-value">{formatBooleanLabel(backlog.audit_status.has_snapshot)}</span>
          <span className="queue-impact-label">Has snapshot</span>
        </div>
        <div className="queue-impact-stat queue-impact-stat--info">
          <span className="queue-impact-value">{backlog.snapshots.length}</span>
          <span className="queue-impact-label">Total snapshots</span>
        </div>
        <div className="queue-impact-stat queue-impact-stat--warning">
          <span className="queue-impact-value">
            {formatAuditStatusValue(backlog.audit_status.next_step.action)}
          </span>
          <span className="queue-impact-label">Next step</span>
        </div>
        <div className="queue-impact-stat queue-impact-stat--positive">
          <span className="queue-impact-value">
            {formatAuditStatusValue(backlog.audit_status.completion_summary.status)}
          </span>
          <span className="queue-impact-label">Completion</span>
        </div>
      </div>

      {latestSnapshots.length === 0 ? (
        <StateNotice
          tone="info"
          title="No review packets yet"
          body={`No persisted review-packet snapshots are available for this patient. Next step: ${formatAuditStatusValue(
            backlog.audit_status.next_step.action,
          )}.`}
        />
      ) : (
        <div className="audit-readiness-table-wrap">
          <table className="audit-readiness-table">
            <thead>
              <tr>
                <th>Created</th>
                <th>Review status</th>
                <th>Review state</th>
                <th>Assigned reviewer</th>
                <th>Audit bundle export</th>
              </tr>
            </thead>
            <tbody>
              {latestSnapshots.map((snapshot) => {
                const unavailableMessage = getAuditBundleUnavailableMessage({ backlog, snapshot });

                return (
                  <tr key={snapshot.id}>
                    <td>{formatDateTime(snapshot.created_at)}</td>
                    <td>{formatAuditStatusValue(snapshot.review_status)}</td>
                    <td>{snapshot.review_state.label}</td>
                    <td>{snapshot.assigned_reviewer_user_id ?? "—"}</td>
                    <td>
                      {unavailableMessage ? (
                        <span>{unavailableMessage}</span>
                      ) : (
                        <>
                          <div
                            className="applied-filters-chips"
                            data-testid="audit-bundle-download-actions"
                          >
                            {AUDIT_BUNDLE_DOWNLOADS.map((download) => (
                              <a
                                key={download.format}
                                className="filter-chip-pill"
                                href={getAuditBundleDownloadHref({
                                  snapshotId: snapshot.id,
                                  format: download.format,
                                })}
                              >
                                {download.label}
                              </a>
                            ))}
                          </div>
                          <p className="inline-helper">
                            Uses approved audit bundle export endpoints. Successful downloads may record
                            audit_bundle_exported events.
                          </p>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
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
  const workflowOutcome = getFirstParam(resolvedSearchParams?.workflow_outcome);
  const initialActionFeedback =
    workflowOutcome && WORKFLOW_OUTCOME_MESSAGES[workflowOutcome]
      ? {
          success: true,
          message: WORKFLOW_OUTCOME_MESSAGES[workflowOutcome],
          outcome: workflowOutcome,
        }
      : null;
  const parsedLimit = limitParam ? Number.parseInt(limitParam, 10) : NaN;
  const pageSize = Number.isFinite(parsedLimit) ? Math.min(Math.max(parsedLimit, 5), 100) : 25;
  const pagePath = `/patients/${patientId}`;
  const originalSearchParams = createSearchParams(resolvedSearchParams, ["workflow_outcome"]);
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

  const timelineFilters: PatientTimelineFilters = {
    ...(eventTypeFilters.length ? { event_types: eventTypeFilters } : {}),
    ...(relatedEscalationFilter ? { related_escalation_id: relatedEscalationFilter } : {}),
    ...(includeOnlyOpenWork ? { include_only_open_work: true } : {}),
  };

  const requestFilters: PatientTimelineFilters = { ...timelineFilters };
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

  let patient: PatientResponse | null = null;
  let worklist: WorklistSummaryResponse | null = null;
  let timeline: TimelineResponse | null = null;
  let auditStatus: PatientAuditStatus | null = null;
  let auditStatusLoadFailed = false;
  let patientBacklog: PatientBacklogDrillInResponse | null = null;
  let patientBacklogLoadFailed = false;
  try {
    [patient, worklist, timeline, auditStatus, patientBacklog] = await Promise.all([
      fetchPatient(patientId, { authRedirectPath: detailRetryHref }),
      fetchWorklistSummary(
        { patientIds: [patientId], limit: 1, activeOnly: false },
        { authRedirectPath: detailRetryHref },
      ),
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
      fetchPatientAuditStatus(patientId, { authRedirectPath: detailRetryHref }).catch((error) => {
        auditStatusLoadFailed = true;
        console.error(`Failed to load audit status for patient ${patientId}`, error);
        return null;
      }),
      fetchPatientBacklogDrillIn(patientId, {}, { authRedirectPath: detailRetryHref }).catch((error) => {
        patientBacklogLoadFailed = true;
        console.error(`Failed to load review packet backlog for patient ${patientId}`, error);
        return null;
      }),
    ]);
  } catch (error) {
    console.error(`Failed to load timeline for patient ${patientId}`, error);
    return (
      <main className="page" data-testid="patient-detail-page">
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

  if (!patient || !worklist || !timeline) {
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
  const validationScenarioPrefix = "validation-scenario:";
  const validationScenario =
    patient.external_patient_id?.startsWith(validationScenarioPrefix)
      ? patient.external_patient_id.slice(validationScenarioPrefix.length).split(":")[0]
      : null;
  const escalationIdFromDetail = detail?.item.related_escalation_id;
  const escalationIdFromEvidence =
    detail?.escalation_evidence?.latest_open_escalation_id ??
    worklistSummary?.latest_open_escalation_id ??
    null;
  const activeEscalationId =
    escalationIdFromDetail ?? relatedEscalationFilter ?? escalationIdFromEvidence ?? null;
  const escalationEvidence = detail?.escalation_evidence ?? null;
  const taskSummary = detail?.task_summary ?? worklistSummary?.task_summary ?? null;
  const workflowStatus = detail?.workflow_status ?? worklistSummary?.workflow_status ?? null;
  const interventionEvidenceSummary = detail?.intervention_evidence_summary ?? null;
  const attentionSummary = detail?.attention_summary ?? null;
  const resolvedAttentionSummary =
    attentionSummary ??
    (worklistSummary
      ? {
          why_now: worklistSummary.attention_reason ?? "No active workflow evidence is currently available.",
          primary_driver: workflowStatus?.primary_driver ?? null,
          recommended_next_action: worklistSummary.next_step ?? "Continue routine monitoring.",
          supporting_evidence: worklistSummary.next_step_reason ? [worklistSummary.next_step_reason] : [],
          urgency_level: workflowStatus?.severity ?? null,
        }
      : null);
  const detailStatusSnapshot = detail?.status_snapshot ?? worklistSummary?.status_snapshot ?? null;
  const detailStatusSnapshotReasonLabel =
    detail?.status_snapshot_reason_label ??
    worklistSummary?.status_snapshot_reason_label ??
    null;
  const detailCareGapLabel = detail?.care_gap_label ?? worklistSummary?.care_gap_label ?? null;
  const detailBlockingIssueLabel =
    detail?.blocking_issue_label ?? worklistSummary?.blocking_issue_label ?? null;
  const detailResolutionTargetLabel =
    detail?.resolution_target_label ?? worklistSummary?.resolution_target_label ?? null;
  const detailClosureReadinessLabel =
    detail?.closure_readiness_label ?? worklistSummary?.closure_readiness_label ?? null;
  const detailClosureReadinessReasonLabel =
    detail?.closure_readiness_reason_label ??
    worklistSummary?.closure_readiness_reason_label ??
    null;
  const detailResolutionConfidenceLabel =
    detail?.resolution_confidence_label ?? worklistSummary?.resolution_confidence_label ?? null;
  const detailResolutionConfidenceReasonLabel =
    detail?.resolution_confidence_reason_label ??
    worklistSummary?.resolution_confidence_reason_label ??
    null;
  const detailLastOperationalChangeLabel =
    detail?.last_operational_change_label ??
    worklistSummary?.last_operational_change_label ??
    null;
  const detailLastOperationalChangeReasonLabel =
    detail?.last_operational_change_reason_label ??
    worklistSummary?.last_operational_change_reason_label ??
    null;
  const detailRecommendedTimeframeReasonLabel =
    detail?.recommended_timeframe_reason_label ??
    worklistSummary?.recommended_timeframe_reason_label ??
    null;
  const detailNextStepReasonDetailLabel =
    detail?.next_step_reason_detail_label ??
    worklistSummary?.next_step_reason_detail_label ??
    null;

  let activeEscalation: PatientEscalation | null = null;
  if (activeEscalationId) {
    try {
      activeEscalation = await fetchEscalation(activeEscalationId, { authRedirectPath: detailRetryHref });
    } catch (error) {
      console.error("Unable to load escalation context", error);
      activeEscalation = null;
    }
  }

  const activeTaskId = taskSummary?.latest_active_task_id ?? null;
  let activeTask: InterventionTask | null = null;
  if (activeTaskId) {
    try {
      activeTask = await fetchInterventionTask(activeTaskId, { authRedirectPath: detailRetryHref });
    } catch (error) {
      console.error("Unable to load intervention task context", error);
      activeTask = null;
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
  ): Promise<ActionResult> => {
    "use server";

    if (!activeEscalationId) {
      return { success: false, message: "No escalation is available for this patient." };
    }

    try {
      if (request.type === "acknowledge") {
        await acknowledgeEscalation(activeEscalationId, {
          authRedirectPath: detailRetryHref,
        });
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
      revalidatePatientViews({ pagePath, detailPath: detailRetryHref });
      const successMessage =
        request.type === "resolve"
          ? WORKFLOW_OUTCOME_MESSAGES.escalation_resolved
          : request.type === "start"
            ? WORKFLOW_OUTCOME_MESSAGES.escalation_started
            : "Escalation acknowledged.";
      const outcome =
        request.type === "resolve"
          ? "escalation_resolved"
          : request.type === "start"
            ? "escalation_started"
            : null;
      return { success: true, message: successMessage, outcome };
    } catch (error) {
      console.error("Failed to update escalation", error);
      return {
        success: false,
        message: error instanceof Error ? error.message : "Unable to update escalation.",
      };
    }
  };

  const taskAction = async (
    request: TaskActionRequest,
  ): Promise<ActionResult> => {
    "use server";

    const targetTaskId = request.taskId ?? activeTaskId;

    if (!targetTaskId) {
      return { success: false, message: "No intervention task is available for this patient." };
    }

    try {
      let updatedTask: InterventionTask | null = null;
      if (request.type === "start") {
        updatedTask = await startInterventionTask(targetTaskId, { authRedirectPath: detailRetryHref });
      } else if (request.type === "cancel") {
        await cancelInterventionTask(targetTaskId, {
          authRedirectPath: detailRetryHref,
        });
        updatedTask = null;
      } else if (request.type === "complete") {
        const completionNote =
          request.note && request.note.trim().length > 0
            ? request.note.trim()
            : "Completed from patient detail workflow controls.";
        await completeInterventionTask(
          targetTaskId,
          {
            completion_note: completionNote,
          },
          { authRedirectPath: detailRetryHref },
        );
        updatedTask = null;
      }
      revalidatePatientViews({ pagePath, detailPath: detailRetryHref });
      const successMessage =
        request.type === "start"
          ? WORKFLOW_OUTCOME_MESSAGES.task_started
          : request.type === "cancel"
            ? "Task canceled."
            : WORKFLOW_OUTCOME_MESSAGES.task_completed;
      const outcome =
        request.type === "start" ? "task_started" : request.type === "complete" ? "task_completed" : null;
      return { success: true, message: successMessage, outcome, ...buildTaskResult(updatedTask) };
    } catch (error) {
      console.error("Failed to update task", error);
      return {
        success: false,
        message: error instanceof Error ? error.message : "Unable to update task.",
      };
    }
  };

  const submitTask = async (
    payload: TaskFormValues,
  ): Promise<ActionResult> => {
    "use server";

    if (!activeEscalationId) {
      return { success: false, message: "An active escalation is required to create a task." };
    }

    const dueAtIso = payload.dueAt ? new Date(payload.dueAt).toISOString() : null;

    try {
      const createdTask = await createInterventionTask(
        activeEscalationId,
        {
          title: payload.title,
          description: payload.description ?? null,
          priority: payload.priority,
          due_at: dueAtIso,
        },
        { authRedirectPath: detailRetryHref },
      );
      revalidatePatientViews({ pagePath, detailPath: detailRetryHref });
      return {
        success: true,
        message: WORKFLOW_OUTCOME_MESSAGES.task_created,
        outcome: "task_created",
        ...buildTaskResult(createdTask),
      };
    } catch (error) {
      console.error("Failed to create task", error);
      return {
        success: false,
        message: error instanceof Error ? error.message : "Unable to create task.",
      };
    }
  };

  return (
    <main className="page" data-testid="patient-detail-page">
      <Link href={queueReturnHref} className="back-link">
        {queueReturnLabel}
      </Link>
      {validationScenario ? (
        <div className="timeline-arrival-context" data-testid="patient-validation-scenario">
          <p className="worklist-context-label">Manual validation</p>
          <p className="timeline-arrival-context-body">Validation scenario: {validationScenario}</p>
        </div>
      ) : null}
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
        <PatientRecentActivityStrip
          latestEvent={latestTimelineEvent}
          summary={worklistSummary}
          taskSummary={taskSummary}
          escalationEvidence={escalationEvidence}
          workflowStatus={workflowStatus}
          activeEscalationStatus={escalationStatus}
        />
      </div>
      <PatientEvidenceSummary evidence={escalationEvidence} summary={worklistSummary} />
      <PatientWhyNowSummary
        summary={resolvedAttentionSummary}
        statusSnapshot={detailStatusSnapshot}
        statusSnapshotReasonLabel={detailStatusSnapshotReasonLabel}
        careGapLabel={detailCareGapLabel}
        blockingIssueLabel={detailBlockingIssueLabel}
        activeOwnerLabel={detail?.active_owner_label ?? worklistSummary?.active_owner_label ?? null}
        waitingOnLabel={detail?.waiting_on_label ?? worklistSummary?.waiting_on_label ?? null}
        nextStepReasonDetailLabel={detailNextStepReasonDetailLabel}
        lastOperationalChangeLabel={detailLastOperationalChangeLabel}
        lastOperationalChangeReasonLabel={detailLastOperationalChangeReasonLabel}
        recommendedTimeframeReasonLabel={detailRecommendedTimeframeReasonLabel}
        resolutionTargetLabel={detailResolutionTargetLabel}
        closureReadinessLabel={detailClosureReadinessLabel}
        closureReadinessReasonLabel={detailClosureReadinessReasonLabel}
        resolutionConfidenceLabel={detailResolutionConfidenceLabel}
        resolutionConfidenceReasonLabel={detailResolutionConfidenceReasonLabel}
      />
      <PatientInterventionEvidenceSummary
        summary={interventionEvidenceSummary}
        workflowStatus={workflowStatus}
      />
      <EscalationEvidenceCard evidence={escalationEvidence} />
      <section className="section-card" data-testid="patient-evidence-chain-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Evidence chain</p>
            <h2 className="section-title">Proof path</h2>
            <p className="section-subtitle">
              Shows whether this patient has the proof chain needed to connect interventions to measurable outcomes.
            </p>
          </div>
        </div>
        {renderEvidenceChainPanel({
          auditStatus,
          auditStatusLoadFailed,
          patientBacklog,
          patientBacklogLoadFailed,
          worklistSummary,
          timeline,
          escalationEvidence,
          taskSummary,
          interventionEvidenceSummary,
        })}
      </section>
      <section className="section-card" data-testid="patient-audit-status-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">ACCESS audit status</p>
            <h2 className="section-title">Review packet readiness</h2>
            <p className="section-subtitle">
              Read-only latest-snapshot audit posture from persisted review packet data.
            </p>
          </div>
        </div>
        {renderAuditStatusPanel({ auditStatus, auditStatusLoadFailed, detailRetryHref })}
      </section>
      <section className="section-card" data-testid="patient-outcome-proof-gaps-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Outcome proof</p>
            <h2 className="section-title">Outcome Proof Gaps</h2>
            <p className="section-subtitle">
              Read-only proof checklist showing which outcome and evidence elements support audit readiness.
            </p>
          </div>
        </div>
        {renderOutcomeProofGapsPanel({
          auditStatus,
          auditStatusLoadFailed,
          patientBacklog,
          patientBacklogLoadFailed,
          worklistSummary,
          timeline,
          escalationEvidence,
          taskSummary,
          interventionEvidenceSummary,
        })}
      </section>
      <section className="section-card" data-testid="patient-manifest-verification-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Manifest verification</p>
            <h2 className="section-title">Audit bundle verification posture</h2>
            <p className="section-subtitle">
              Shows whether the persisted review packet and audit bundle posture can support verification without changing workflow state.
            </p>
          </div>
        </div>
        {renderManifestVerificationPanel({ auditStatus, auditStatusLoadFailed })}
      </section>
      <section className="section-card" data-testid="patient-review-packet-backlog-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Review packet backlog</p>
            <h2 className="section-title">Packet drill-in</h2>
            <p className="section-subtitle">
              Read-only snapshot backlog for this patient from persisted review packet data.
            </p>
          </div>
        </div>
        {renderPatientBacklogPanel({
          backlog: patientBacklog,
          backlogLoadFailed: patientBacklogLoadFailed,
          detailRetryHref,
        })}
      </section>
      <section className="section-card">
        <div className="section-header">
          <div>
            <p className="eyebrow">Escalation actions</p>
            <h2 className="section-title">Current escalation</h2>
            <p className="section-subtitle">Act on the escalation and capture intervention work.</p>
          </div>
        </div>
        <PatientActionControls
          escalationStatus={escalationStatus}
          task={activeTask}
          taskSummary={taskSummary}
          patientName={patientName}
          initialFeedback={initialActionFeedback}
          createTaskContextLabel={createTaskContextLabel}
          disableTaskCreation={!activeEscalationId}
          disabledCreateTaskMessage="Tasks are created when a patient has an open escalation."
          onEscalationAction={escalationAction}
          onTaskAction={taskAction}
          onCreateTask={submitTask}
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
