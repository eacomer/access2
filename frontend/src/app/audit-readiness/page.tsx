import Link from "next/link";
import { Suspense } from "react";

import StateNotice from "../../components/StateNotice";
import { fetchAuditReadiness, fetchReviewerMySummary } from "../../lib/api";
import { requireAuth } from "../../lib/auth/session";
import { formatDateTime, formatPriority } from "../../lib/format";
import type { AuditReadinessItem, AuditReadinessStatus, ReviewerMySummary } from "../../types/patient";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

const STATUS_OPTIONS: Array<{ value: AuditReadinessStatus; label: string }> = [
  { value: "incomplete", label: "Incomplete" },
  { value: "review_ready", label: "Review ready" },
  { value: "approved_not_exported", label: "Approved, not exported" },
  { value: "audit_ready", label: "Audit ready" },
  { value: "rejected", label: "Rejected" },
];

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

const getFirstParam = (value?: string | string[]): string | undefined => {
  if (!value) {
    return undefined;
  }
  return Array.isArray(value) ? value[0] : value;
};

const parseStatus = (value?: string | string[]): AuditReadinessStatus | undefined => {
  const raw = getFirstParam(value);
  if (!raw) {
    return undefined;
  }
  return STATUS_OPTIONS.some((option) => option.value === raw) ? (raw as AuditReadinessStatus) : undefined;
};

const formatValue = (value?: string | null) => value || "—";

const formatAuditStatusValue = (value?: string | null) =>
  value
    ? value
        .split("_")
        .filter(Boolean)
        .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
        .join(" ")
    : "—";

const formatExportFormats = (item: AuditReadinessItem) => {
  if (!item.audit_bundle.export_formats.length) {
    return "—";
  }
  return item.audit_bundle.export_formats.join(", ");
};

const patientDetailHref = (patientId: string) => `/patients/${encodeURIComponent(patientId)}`;

const statusHref = (status?: AuditReadinessStatus) =>
  status ? `/audit-readiness?status=${encodeURIComponent(status)}` : "/audit-readiness";

const renderReviewerSummaryStats = (summary: ReviewerMySummary) => (
  <div className="queue-impact-grid">
    <div className="queue-impact-stat queue-impact-stat--info">
      <span className="queue-impact-value">{summary.assigned_to_me_count}</span>
      <span className="queue-impact-label">Assigned to me</span>
    </div>
    <div className="queue-impact-stat queue-impact-stat--positive">
      <span className="queue-impact-value">{summary.pending_assigned_ready_count}</span>
      <span className="queue-impact-label">Ready to review</span>
    </div>
    <div className="queue-impact-stat queue-impact-stat--alert">
      <span className="queue-impact-value">{summary.blocked_missing_evidence_count}</span>
      <span className="queue-impact-label">Blocked or missing evidence</span>
    </div>
    <div className="queue-impact-stat queue-impact-stat--warning">
      <span className="queue-impact-value">{summary.pending_review_age.over_seven_days_count}</span>
      <span className="queue-impact-label">Stale reviews</span>
    </div>
    <div className="queue-impact-stat">
      <span className="queue-impact-value">{summary.pending_review_age.new_today_count}</span>
      <span className="queue-impact-label">New today</span>
    </div>
    <div className="queue-impact-stat">
      <span className="queue-impact-value">{summary.pending_review_age.one_to_three_days_count}</span>
      <span className="queue-impact-label">1-3 days pending</span>
    </div>
    <div className="queue-impact-stat">
      <span className="queue-impact-value">{summary.pending_review_age.four_to_seven_days_count}</span>
      <span className="queue-impact-label">4-7 days pending</span>
    </div>
  </div>
);

const ReviewerSummaryLoading = () => (
  <section className="queue-impact" aria-label="Reviewer workload summary">
    <div className="queue-impact-head">
      <div>
        <p className="worklist-context-label">Reviewer workload</p>
        <p className="queue-impact-summary">Loading assigned review summary.</p>
      </div>
    </div>
  </section>
);

async function ReviewerSummarySection({ retryHref }: { retryHref: string }) {
  let summary: ReviewerMySummary | null = null;
  try {
    summary = await fetchReviewerMySummary({ authRedirectPath: retryHref });
  } catch (error) {
    if (isRedirectLikeError(error)) {
      throw error;
    }
    console.error("Failed to load reviewer summary", error);
    return (
      <StateNotice
        tone="warning"
        title="Reviewer summary unavailable"
        body="The reviewer workload request failed. Audit-readiness rows remain available."
      />
    );
  }

  return (
    <section className="queue-impact" aria-label="Reviewer workload summary">
      <div className="queue-impact-head">
        <div>
          <p className="worklist-context-label">Reviewer workload</p>
          <p className="queue-impact-summary">
            Assigned review posture for the current reviewer from persisted packet state.
          </p>
        </div>
        <p className="worklist-context-helper">
          Oldest pending snapshot: {formatDateTime(summary.oldest_pending_snapshot_created_at)}
        </p>
      </div>
      {renderReviewerSummaryStats(summary)}
    </section>
  );
}

export default async function AuditReadinessPage({ searchParams }: PageProps) {
  const resolvedSearchParams =
    (searchParams ? await searchParams : {}) as Record<string, string | string[] | undefined>;
  const selectedStatus = parseStatus(resolvedSearchParams.status);
  const retryHref = statusHref(selectedStatus);

  await requireAuth(retryHref);

  try {
    const payload = await fetchAuditReadiness(
      {
        status: selectedStatus,
        limit: 50,
        offset: 0,
      },
      { authRedirectPath: retryHref },
    );

    const counts = payload.status_counts;

    return (
      <main className="page" data-testid="audit-readiness-page">
        <header className="patient-workflow-header">
          <div className="patient-workflow-header-main">
            <p className="eyebrow">ACCESS review packets</p>
            <h1>Audit readiness</h1>
            <p className="patient-workflow-header-subtitle">
              Read-only latest-per-patient readiness view from persisted snapshot and event data.
            </p>
          </div>
          <div className="patient-workflow-cues" aria-label="Audit readiness filters">
            <Link className="filter-chip-pill" href={statusHref()}>
              All
            </Link>
            {STATUS_OPTIONS.map((option) => (
              <Link
                aria-current={selectedStatus === option.value ? "page" : undefined}
                className="filter-chip-pill"
                href={statusHref(option.value)}
                key={option.value}
              >
                {option.label}
              </Link>
            ))}
          </div>
        </header>

        <Suspense fallback={<ReviewerSummaryLoading />}>
          <ReviewerSummarySection retryHref={retryHref} />
        </Suspense>

        <section className="queue-impact" aria-label="Audit readiness status counts">
          <div className="queue-impact-head">
            <div>
              <p className="worklist-context-label">Status counts</p>
              <p className="queue-impact-summary">
                Counts are latest-per-patient and are not affected by pagination.
              </p>
            </div>
          </div>
          <div className="queue-impact-grid">
            <div className="queue-impact-stat queue-impact-stat--alert">
              <span className="queue-impact-value">{counts.incomplete_count}</span>
              <span className="queue-impact-label">Incomplete</span>
            </div>
            <div className="queue-impact-stat queue-impact-stat--info">
              <span className="queue-impact-value">{counts.review_ready_count}</span>
              <span className="queue-impact-label">Review ready</span>
            </div>
            <div className="queue-impact-stat queue-impact-stat--warning">
              <span className="queue-impact-value">{counts.approved_not_exported_count}</span>
              <span className="queue-impact-label">Approved, not exported</span>
            </div>
            <div className="queue-impact-stat queue-impact-stat--positive">
              <span className="queue-impact-value">{counts.audit_ready_count}</span>
              <span className="queue-impact-label">Audit ready</span>
            </div>
            <div className="queue-impact-stat">
              <span className="queue-impact-value">{counts.rejected_count}</span>
              <span className="queue-impact-label">Rejected</span>
            </div>
          </div>
        </section>

        <section className="worklist-results" aria-label="Audit readiness worklist">
          <div className="worklist-results-head">
            <div>
              <p className="worklist-context-label">Worklist rows</p>
              <p className="worklist-context-helper">
                Showing {payload.items.length} of {payload.total_count} persisted latest-snapshot rows.
              </p>
            </div>
          </div>
          {payload.items.length === 0 ? (
            <StateNotice
              tone="info"
              title="No audit-readiness rows"
              body="No persisted latest snapshots match the current status filter."
            />
          ) : (
            <div className="audit-readiness-table-wrap">
              <table className="audit-readiness-table">
                <thead>
                  <tr>
                    <th>Patient ID</th>
                    <th>Latest Snapshot ID</th>
                    <th>Snapshot Created</th>
                    <th>Review Status</th>
                    <th>Completion</th>
                    <th>Review State</th>
                    <th>Reviewer</th>
                    <th>Next Step</th>
                    <th>Priority</th>
                    <th>Bundle Available</th>
                    <th>Exported</th>
                    <th>Formats</th>
                  </tr>
                </thead>
                <tbody>
                  {payload.items.map((item) => (
                    <tr key={item.latest_snapshot_id}>
                      <td>
                        <Link className="table-link" href={patientDetailHref(item.patient_id)}>
                          {item.patient_id}
                        </Link>
                      </td>
                      <td>{item.latest_snapshot_id}</td>
                      <td>{formatDateTime(item.latest_snapshot_created_at)}</td>
                      <td>{formatAuditStatusValue(item.review_status)}</td>
                      <td>{formatAuditStatusValue(item.completion_status)}</td>
                      <td>{formatAuditStatusValue(item.review_state)}</td>
                      <td>{formatValue(item.assigned_reviewer_user_id)}</td>
                      <td>
                        <strong>{formatAuditStatusValue(item.next_step.action)}</strong>
                        <p className="inline-helper">{item.next_step.reason}</p>
                      </td>
                      <td>{formatPriority(item.next_step.priority)}</td>
                      <td>{item.audit_bundle.available ? "Yes" : "No"}</td>
                      <td>{item.audit_bundle.exported ? "Yes" : "No"}</td>
                      <td>{formatExportFormats(item)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    );
  } catch (error) {
    if (isRedirectLikeError(error)) {
      throw error;
    }
    console.error("Failed to load audit readiness dashboard", error);
    return (
      <main className="page" data-testid="audit-readiness-page">
        <header className="patient-workflow-header">
          <div className="patient-workflow-header-main">
            <p className="eyebrow">ACCESS review packets</p>
            <h1>Audit readiness</h1>
            <p className="patient-workflow-header-subtitle">
              Read-only latest-per-patient readiness view from persisted snapshot and event data.
            </p>
          </div>
        </header>
        <StateNotice
          tone="danger"
          title="Unable to load audit readiness"
          body="The backend request failed. Retry or check that the backend service is healthy."
          actions={[{ label: "Retry", href: retryHref }]}
        />
      </main>
    );
  }
}
