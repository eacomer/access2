"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

export type ReviewPacketSnapshotCreateControlEligibility = {
  latestSnapshotId?: string | null;
  nextStepAction?: string | null;
  patientId: string;
  reviewStatus?: string | null;
};

export const canRenderReviewPacketSnapshotCreateControl = ({
  latestSnapshotId,
  nextStepAction,
  patientId,
  reviewStatus,
}: ReviewPacketSnapshotCreateControlEligibility) =>
  Boolean(patientId) &&
  nextStepAction === "create_snapshot" &&
  (reviewStatus === "rejected" || (!latestSnapshotId && reviewStatus == null));

type ReviewPacketSnapshotCreateControlProps = ReviewPacketSnapshotCreateControlEligibility;

const toErrorMessage = (payload: unknown, fallback: string) => {
  if (payload && typeof payload === "object" && "error" in payload) {
    const error = (payload as { error?: unknown }).error;
    if (typeof error === "string" && error.trim()) {
      return error;
    }
  }
  return fallback;
};

export default function ReviewPacketSnapshotCreateControl({
  latestSnapshotId,
  nextStepAction,
  patientId,
  reviewStatus,
}: ReviewPacketSnapshotCreateControlProps) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPending, startTransition] = useTransition();

  if (
    !canRenderReviewPacketSnapshotCreateControl({
      latestSnapshotId,
      nextStepAction,
      patientId,
      reviewStatus,
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
      const response = await fetch(`/review-packet-snapshots/patients/${encodeURIComponent(patientId)}/create`, {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
      });
      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        setError(toErrorMessage(payload, "Review packet snapshot creation failed."));
        return;
      }

      setSuccess("New review packet snapshot created.");
      startTransition(() => {
        router.refresh();
      });
    } catch {
      setError("Review packet snapshot creation failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form
      className="form-stack"
      data-testid="review-packet-snapshot-create-control"
      onSubmit={handleSubmit}
    >
      <p className="inline-helper">
        Creates a new immutable packet from current evidence. Existing packet JSON and Markdown stay preserved.
      </p>
      <div className="form-footer">
        <button className="button button--primary" disabled={isSubmitting || isPending} type="submit">
          {isSubmitting || isPending ? "Creating..." : "Create new review packet snapshot"}
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
