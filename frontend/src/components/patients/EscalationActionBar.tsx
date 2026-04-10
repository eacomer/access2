"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { EscalationStatus } from "../../types/patient";
import type { ActionResult } from "./ActionFeedbackBanner";

export type EscalationActionRequest = {
  type: "acknowledge" | "start" | "resolve";
  note?: string | null;
};

type Props = {
  status: EscalationStatus | null;
  onAction: (request: EscalationActionRequest) => Promise<ActionResult>;
  onFeedback?: (result: ActionResult | null) => void;
};

const formatStatus = (status: EscalationStatus | null): string => {
  if (!status) {
    return "Not available";
  }
  return status
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
};

export default function EscalationActionBar({ status, onAction, onFeedback }: Props) {
  const router = useRouter();
  const [resolutionNote, setResolutionNote] = useState("");
  const [isPending, setIsPending] = useState(false);

  const canAcknowledge = status === "open";
  const canStart = status === "open";
  const canResolve = status === "open" || status === "in_progress";

  if (!status) {
    return <p className="empty-state">No escalation context available for this patient yet.</p>;
  }

  if (status === "resolved" || status === "canceled") {
    return (
      <div>
        <p className="inline-helper">
          Latest escalation is already {formatStatus(status).toLowerCase()}.
        </p>
      </div>
    );
  }

  const runAction = async (type: EscalationActionRequest["type"]) => {
    onFeedback?.(null);
    setIsPending(true);
    try {
      const result = await onAction({
        type,
        note: type === "resolve" ? resolutionNote.trim() || null : null,
      });
      onFeedback?.(result);
      if (result.success) {
        if (type === "resolve") {
          setResolutionNote("");
        }
        router.refresh();
      }
    } catch (error) {
      onFeedback?.({
        success: false,
        message: "Something went wrong while updating the escalation.",
      });
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className="action-panel">
      <div>
        <p className="inline-helper">Current status: {formatStatus(status)}</p>
      </div>
      <div className="action-bar">
        {canAcknowledge && (
          <button
            type="button"
            className="button button--subtle"
            disabled={isPending}
            onClick={() => runAction("acknowledge")}
          >
            Acknowledge
          </button>
        )}
        {canStart && (
          <button
            type="button"
            className="button button--primary"
            disabled={isPending}
            onClick={() => runAction("start")}
          >
            Move to in progress
          </button>
        )}
        {canResolve && (
          <button
            type="button"
            className="button button--danger"
            disabled={isPending}
            onClick={() => runAction("resolve")}
          >
            Resolve
          </button>
        )}
      </div>
      {canResolve && (
        <div className="form-field">
          <label htmlFor="resolution-note">Resolution notes (optional)</label>
          <textarea
            id="resolution-note"
            className="form-control"
            rows={2}
            placeholder="Record final notes for this escalation"
            value={resolutionNote}
            disabled={isPending}
            onChange={(event) => setResolutionNote(event.target.value)}
          />
        </div>
      )}
    </div>
  );
}
