"use client";

import { FormEvent, useState } from "react";

export type ReviewerAssignmentControlEligibility = {
  latestSnapshotId?: string | null;
  reviewStatus?: string | null;
  snapshotId: string;
};

export const canRenderReviewerAssignmentControl = ({
  latestSnapshotId,
  reviewStatus,
  snapshotId,
}: ReviewerAssignmentControlEligibility) =>
  Boolean(snapshotId) && snapshotId === latestSnapshotId && reviewStatus === "pending_review";

type ReviewerAssignmentControlProps = ReviewerAssignmentControlEligibility;

const toErrorMessage = (payload: unknown, fallback: string) => {
  if (payload && typeof payload === "object" && "error" in payload) {
    const error = (payload as { error?: unknown }).error;
    if (typeof error === "string" && error.trim()) {
      return error;
    }
  }
  return fallback;
};

export default function ReviewerAssignmentControl({
  latestSnapshotId,
  reviewStatus,
  snapshotId,
}: ReviewerAssignmentControlProps) {
  const [reviewerUserId, setReviewerUserId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!canRenderReviewerAssignmentControl({ latestSnapshotId, reviewStatus, snapshotId })) {
    return null;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedReviewerUserId = reviewerUserId.trim();
    if (!trimmedReviewerUserId) {
      setSuccess(null);
      setError("Reviewer user ID required.");
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSubmitting(true);
    try {
      const response = await fetch(`/review-packet-snapshots/${encodeURIComponent(snapshotId)}/assignment`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ assigned_reviewer_user_id: trimmedReviewerUserId }),
      });
      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        setError(toErrorMessage(payload, "Review packet snapshot assignment failed."));
        return;
      }

      setReviewerUserId("");
      setSuccess("Reviewer assigned.");
    } catch {
      setError("Review packet snapshot assignment failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="form-stack" data-testid="reviewer-assignment-control" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor={`reviewer-user-id-${snapshotId}`}>V2 controlled reviewer assignment</label>
        <input
          className="form-control"
          id={`reviewer-user-id-${snapshotId}`}
          name="assignedReviewerUserId"
          onChange={(event) => setReviewerUserId(event.target.value)}
          type="text"
          value={reviewerUserId}
        />
        <p className="inline-helper">Reviewer user ID from the same tenant required.</p>
      </div>
      <div className="form-footer">
        <button className="button button--primary" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Assigning..." : "Assign reviewer"}
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
