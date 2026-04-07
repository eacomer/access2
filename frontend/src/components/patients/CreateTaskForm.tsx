"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import type { InterventionTaskPriority } from "../../types/patient";

export type TaskFormValues = {
  title: string;
  priority: InterventionTaskPriority;
  description?: string;
  dueAt?: string | null;
};

type ActionResult = {
  success: boolean;
  message?: string;
};

type Props = {
  patientName: string;
  contextLabel?: string;
  disabled?: boolean;
  disabledMessage?: string;
  onCreate: (values: TaskFormValues) => Promise<ActionResult>;
};

const createDefaultValues = (): TaskFormValues => ({
  title: "",
  priority: "medium",
  description: "",
  dueAt: null,
});

export default function CreateTaskForm({
  patientName,
  contextLabel,
  disabled = false,
  disabledMessage,
  onCreate,
}: Props) {
  const router = useRouter();
  const [values, setValues] = useState<TaskFormValues>(createDefaultValues);
  const [feedback, setFeedback] = useState<ActionResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const resetForm = () => {
    setValues(createDefaultValues());
    setFeedback(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (disabled || !values.title.trim() || isSubmitting) {
      return;
    }
    setFeedback(null);
    setIsSubmitting(true);
    try {
      const result = await onCreate({
        ...values,
        title: values.title.trim(),
        description: values.description?.trim() ? values.description.trim() : undefined,
        dueAt: values.dueAt && values.dueAt.length > 0 ? values.dueAt : null,
      });
      setFeedback(result);
      if (result.success) {
        resetForm();
        router.refresh();
      }
    } catch (error) {
      setFeedback({
        success: false,
        message: "Unable to create task. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const setField = <K extends keyof TaskFormValues>(field: K, value: TaskFormValues[K]) => {
    setValues((prev) => ({ ...prev, [field]: value }));
  };

  const isSubmitDisabled = disabled || !values.title.trim() || isSubmitting;

  return (
    <form className="form-stack" onSubmit={handleSubmit}>
      <p className="inline-helper">
        New intervention task for {patientName}
        {contextLabel ? ` · ${contextLabel}` : ""}
      </p>
      <div className="form-field">
        <label htmlFor="task-title">Task title</label>
        <input
          id="task-title"
          className="form-control"
          type="text"
          placeholder="Example: Call patient to confirm medication plan"
          value={values.title}
          disabled={disabled || isSubmitting}
          onChange={(event) => setField("title", event.target.value)}
          required
        />
      </div>
      <div className="form-grid">
        <div className="form-field">
          <label htmlFor="task-priority">Priority</label>
          <select
            id="task-priority"
            className="form-control"
            value={values.priority}
            disabled={disabled || isSubmitting}
            onChange={(event) => setField("priority", event.target.value as InterventionTaskPriority)}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="task-due-at">Due by</label>
          <input
            id="task-due-at"
            className="form-control"
            type="datetime-local"
            value={values.dueAt ?? ""}
            disabled={disabled || isSubmitting}
            onChange={(event) => setField("dueAt", event.target.value || null)}
          />
        </div>
      </div>
      <div className="form-field">
        <label htmlFor="task-description">Notes (optional)</label>
        <textarea
          id="task-description"
          className="form-control"
          rows={2}
          placeholder="Add any quick context to keep the queue actionable"
          value={values.description ?? ""}
          disabled={disabled || isSubmitting}
          onChange={(event) => setField("description", event.target.value)}
        />
      </div>
      <div className="form-footer">
        <button type="submit" className="button button--primary" disabled={isSubmitDisabled}>
          Create task
        </button>
        <button
          type="button"
          className="button button--ghost"
          disabled={disabled || isPending}
          onClick={resetForm}
        >
          Cancel
        </button>
      </div>
      {feedback && (
        <p
          className={`form-feedback ${
            feedback.success ? "form-feedback--success" : "form-feedback--error"
          }`}
        >
          {feedback.message}
        </p>
      )}
      {disabled && disabledMessage && (
        <p className="form-feedback form-feedback--muted">{disabledMessage}</p>
      )}
    </form>
  );
}
