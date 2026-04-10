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
  createTaskContextLabel,
  disableTaskCreation = false,
  disabledCreateTaskMessage,
  onEscalationAction,
  onTaskAction,
  onCreateTask,
}: Props) {
  const [feedback, setFeedback] = useState<ActionResult | null>(null);

  const handleFeedback = (result: ActionResult | null) => {
    setFeedback(result);
  };

  return (
    <div className="patient-action-controls">
      <ActionFeedbackBanner feedback={feedback} onDismiss={() => setFeedback(null)} />
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
