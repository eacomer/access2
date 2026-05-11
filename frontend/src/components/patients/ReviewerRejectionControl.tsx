"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

export type ReviewerRejectionControlEligibility = {
  latestSnapshotId?: string | null;
  reviewStatus?: string | null;
  snapshotId: string;
};

export const canRenderReviewerRejectionControl = ({
  latestSnapshotId,
  reviewStatus,
  snapshotId,
}: ReviewerRejectionControlEligibility) =>
  Boolean(snapshotId) && snapshotId === latestSnapshotId && reviewStatus === "pending_review";

type ReviewerRejectionControlProps = ReviewerRejectionControlEligibility;

const toErrorMessage = (payload: unknown, fallback: string) => {
  if (payload && typeof payload === "object" && "error" in payload) {
    const error = (payload as { error?: unknown }).error;
    if (typeof error === "string" && error.trim()) {
      return error;
    }
  }
  return fallback;
};

export default function ReviewerRejectionControl({
  latestSnapshotId,
  reviewStatus,
  snapshotId,
}: ReviewerRejectionControlProps) {
  const router = useRouter();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPending, startTransition] = useTransition();

  if (!canRenderReviewerRejectionControl({ latestSnapshotId, reviewStatus, snapshotId })) {
    return null;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedReason = reason.trim();
    if (!trimmedReason) {
      setError("Rejection reason required.");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      const response = await fetch(`/review-packet-snapshots/${encodeURIComponent(snapshotId)}/reject`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reason: trimmedReason }),
      });
      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        setError(toErrorMessage(payload, "Review packet snapshot rejection failed."));
        return;
      }

      setReason("");
      startTransition(() => {
        router.refresh();
      });
    } catch {
      setError("Review packet snapshot rejection failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="form-stack" data-testid="reviewer-rejection-control" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor={`rejection-reason-${snapshotId}`}>V2 controlled reviewer rejection</label>
        <textarea
          className="form-control"
          id={`rejection-reason-${snapshotId}`}
          name="reason"
          onChange={(event) => setReason(event.target.value)}
          rows={3}
          value={reason}
        />
        <p className="inline-helper">Rejection reason required.</p>
      </div>
      <div className="form-footer">
        <button className="button button--primary" disabled={isSubmitting || isPending} type="submit">
          {isSubmitting || isPending ? "Rejecting..." : "Reject snapshot"}
        </button>
      </div>
      {error ? (
        <div className="action-feedback action-feedback--error" role="alert">
          <p className="form-feedback form-feedback--error">{error}</p>
        </div>
      ) : null}
    </form>
  );
}
