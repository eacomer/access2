"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type ReviewChecklist = {
  missing_count?: unknown;
};

type PacketJsonWithChecklist = {
  review_checklist?: ReviewChecklist;
};

export type ReviewPacketSnapshotApprovalControlEligibility = {
  latestSnapshotId?: string | null;
  packetJson?: Record<string, unknown> | null;
  reviewStatus?: string | null;
  snapshotId: string;
};

const getMissingEvidenceCount = (packetJson?: Record<string, unknown> | null) => {
  const reviewChecklist = (packetJson as PacketJsonWithChecklist | null | undefined)?.review_checklist;
  const missingCount = reviewChecklist?.missing_count;
  if (typeof missingCount === "number" && Number.isFinite(missingCount)) {
    return missingCount;
  }
  if (typeof missingCount === "string" && missingCount.trim()) {
    const parsed = Number.parseInt(missingCount, 10);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

export const canRenderReviewPacketSnapshotApprovalControl = ({
  latestSnapshotId,
  packetJson,
  reviewStatus,
  snapshotId,
}: ReviewPacketSnapshotApprovalControlEligibility) =>
  Boolean(snapshotId) &&
  snapshotId === latestSnapshotId &&
  reviewStatus === "pending_review" &&
  getMissingEvidenceCount(packetJson) === 0;

type ReviewPacketSnapshotApprovalControlProps = ReviewPacketSnapshotApprovalControlEligibility;

const toErrorMessage = (payload: unknown, fallback: string) => {
  if (payload && typeof payload === "object" && "error" in payload) {
    const error = (payload as { error?: unknown }).error;
    if (typeof error === "string" && error.trim()) {
      return error;
    }
  }
  return fallback;
};

export default function ReviewPacketSnapshotApprovalControl({
  latestSnapshotId,
  packetJson,
  reviewStatus,
  snapshotId,
}: ReviewPacketSnapshotApprovalControlProps) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPending, startTransition] = useTransition();

  if (
    !canRenderReviewPacketSnapshotApprovalControl({
      latestSnapshotId,
      packetJson,
      reviewStatus,
      snapshotId,
    })
  ) {
    return null;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);
    try {
      const response = await fetch(`/review-packet-snapshots/${encodeURIComponent(snapshotId)}/approve`, {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
      });
      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        setError(toErrorMessage(payload, "Review packet snapshot approval failed."));
        return;
      }

      setSuccess("Review packet snapshot approved.");
      startTransition(() => {
        router.refresh();
      });
    } catch {
      setError("Review packet snapshot approval failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="form-stack" data-testid="review-packet-snapshot-approval-control" onSubmit={handleSubmit}>
      <p className="inline-helper">
        Approves the latest pending packet only when the persisted review checklist has no missing evidence.
      </p>
      <div className="form-footer">
        <button className="button button--primary" disabled={isSubmitting || isPending} type="submit">
          {isSubmitting || isPending ? "Approving..." : "Approve snapshot"}
        </button>
      </div>
      {error ? (
        <div className="action-feedback action-feedback--error" role="alert">
          <p className="form-feedback form-feedback--error">{error}</p>
        </div>
      ) : null}
      {success ? (
        <div className="action-feedback action-feedback--success" role="status">
          <p className="form-feedback form-feedback--success">{success}</p>
        </div>
      ) : null}
    </form>
  );
}
