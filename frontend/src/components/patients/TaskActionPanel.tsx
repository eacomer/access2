"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import type { InterventionTask, PatientInterventionTaskSummary } from "../../types/patient";
import type { ActionResult } from "./ActionFeedbackBanner";

export type TaskActionRequest = {
  type: "start" | "complete" | "cancel";
  note?: string | null;
};

type Props = {
  task: InterventionTask | null;
  taskSummary: PatientInterventionTaskSummary | null;
  onAction: (request: TaskActionRequest) => Promise<ActionResult>;
  onFeedback?: (result: ActionResult | null) => void;
};

const formatTaskStatus = (status: string | null | undefined): string => {
  if (!status) {
    return "Not available";
  }
  return status
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
};

export default function TaskActionPanel({ task, taskSummary, onAction, onFeedback }: Props) {
  const router = useRouter();
  const [completionNote, setCompletionNote] = useState("");
  const [isPending, setIsPending] = useState(false);

  const resolvedStatus = useMemo(() => {
    const status = task?.status ?? taskSummary?.latest_active_task_status ?? null;
    return status ? status.toLowerCase() : null;
  }, [task?.status, taskSummary?.latest_active_task_status]);

  const canStart = resolvedStatus === "open";
  const canComplete = resolvedStatus === "open" || resolvedStatus === "in_progress";
  const canCancel = resolvedStatus === "open" || resolvedStatus === "in_progress";
  const hasActionButtons = canStart || canComplete || canCancel;
  const title = task?.title ?? taskSummary?.latest_active_task_title ?? "Intervention task";

  const runAction = async (type: TaskActionRequest["type"]) => {
    onFeedback?.(null);
    setIsPending(true);
    try {
      const result = await onAction({
        type,
        note: type === "complete" ? completionNote.trim() || null : null,
      });
      onFeedback?.(result);
      if (result.success) {
        if (type === "complete") {
          setCompletionNote("");
        }
        router.refresh();
      }
    } catch (error) {
      onFeedback?.({
        success: false,
        message: "Unable to update the task right now.",
      });
    } finally {
      setIsPending(false);
    }
  };

  if (!task) {
    return (
      <div className="action-panel">
        <p className="inline-helper">
          No active task is available. Create a task or wait for workflow assignments.
        </p>
      </div>
    );
  }

  return (
    <div className="action-panel" style={{ marginTop: "1rem" }}>
      <div>
        <p className="inline-helper">
          Latest task: <strong>{title}</strong>
        </p>
        <p className="inline-helper">Current status: {formatTaskStatus(task.status)}</p>
      </div>
      {hasActionButtons ? (
        <>
          <div className="action-bar">
            {canStart && (
              <button
                type="button"
                className="button button--primary"
                disabled={isPending}
                onClick={() => runAction("start")}
              >
                Start task
              </button>
            )}
            {canComplete && (
              <button
                type="button"
                className="button button--danger"
                disabled={isPending}
                onClick={() => runAction("complete")}
              >
                Complete task
              </button>
            )}
            {canCancel && (
              <button
                type="button"
                className="button button--ghost"
                disabled={isPending}
                onClick={() => runAction("cancel")}
              >
                Cancel task
              </button>
            )}
          </div>
          {canComplete ? (
            <div className="form-field">
              <label htmlFor="task-completion-note">Completion note (optional)</label>
              <textarea
                id="task-completion-note"
                className="form-control"
                rows={2}
                placeholder="Record the outcome of this task"
                value={completionNote}
                disabled={isPending}
                onChange={(event) => setCompletionNote(event.target.value)}
              />
            </div>
          ) : null}
        </>
      ) : (
        <p className="inline-helper">
          This task is already {formatTaskStatus(task.status).toLowerCase()}.
        </p>
      )}
    </div>
  );
}
