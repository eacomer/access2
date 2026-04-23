"use client";

import { useState } from "react";

import type {
  EscalationStatus,
  InterventionTask,
  PatientInterventionTaskSummary,
} from "../../types/patient";
import ActionFeedbackBanner, { ActionResult } from "./ActionFeedbackBanner";
import EscalationActionBar, { EscalationActionRequest } from "./EscalationActionBar";
import TaskActionPanel, { TaskActionRequest } from "./TaskActionPanel";
import CreateTaskForm, { TaskFormValues } from "./CreateTaskForm";

type Props = {
  escalationStatus: EscalationStatus | null;
  task: InterventionTask | null;
  taskSummary: PatientInterventionTaskSummary | null;
  patientName: string;
  initialFeedback?: ActionResult | null;
  createTaskContextLabel?: string;
  disableTaskCreation?: boolean;
  disabledCreateTaskMessage?: string;
  onEscalationAction: (request: EscalationActionRequest) => Promise<ActionResult>;
  onTaskAction: (request: TaskActionRequest) => Promise<ActionResult>;
  onCreateTask: (values: TaskFormValues) => Promise<ActionResult>;
};

export default function PatientActionControls({
  escalationStatus,
  task,
  taskSummary,
  patientName,
  initialFeedback = null,
  createTaskContextLabel,
  disableTaskCreation = false,
  disabledCreateTaskMessage,
  onEscalationAction,
  onTaskAction,
  onCreateTask,
}: Props) {
  const [feedback, setFeedback] = useState<ActionResult | null>(initialFeedback);

  const clearOutcomeParam = () => {
    if (typeof window === "undefined") {
      return;
    }
    const url = new URL(window.location.href);
    if (url.searchParams.has("workflow_outcome")) {
      url.searchParams.delete("workflow_outcome");
      window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
    }
  };

  const handleFeedback = (result: ActionResult | null) => {
    if (result === null) {
      clearOutcomeParam();
    } else if (result.success && result.outcome && typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("workflow_outcome", result.outcome);
      window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
    }
    setFeedback(result);
  };

  return (
    <div className="patient-action-controls">
      <ActionFeedbackBanner
        feedback={feedback}
        onDismiss={() => {
          clearOutcomeParam();
          setFeedback(null);
        }}
      />
      <EscalationActionBar
        status={escalationStatus}
        onAction={onEscalationAction}
        onFeedback={handleFeedback}
      />
      <TaskActionPanel
        task={task}
        taskSummary={taskSummary}
        onAction={onTaskAction}
        onFeedback={handleFeedback}
      />
      <CreateTaskForm
        patientName={patientName}
        contextLabel={createTaskContextLabel}
        disabled={disableTaskCreation}
        disabledMessage={disabledCreateTaskMessage}
        onCreate={onCreateTask}
        onFeedback={handleFeedback}
      />
    </div>
  );
}
