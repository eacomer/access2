"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

import type {
  WorkflowBootstrapCreateResponse,
  WorkflowBootstrapEscalationSeverity,
  WorkflowBootstrapSignalType,
} from "../../types/admin";
import type { InterventionTaskPriority } from "../../types/patient";

export type WorkflowBootstrapFormValues = {
  firstName: string;
  lastName: string;
  dateOfBirth: string;
  signalType: WorkflowBootstrapSignalType;
  signalNotes?: string;
  escalationSeverity: WorkflowBootstrapEscalationSeverity;
  createOpenTask: boolean;
  taskTitle?: string;
  taskDescription?: string;
  taskPriority: InterventionTaskPriority;
  taskDueAt?: string | null;
};

type SubmitResult = {
  success: boolean;
  message?: string;
  response?: WorkflowBootstrapCreateResponse | null;
};

type Props = {
  onSubmit: (values: WorkflowBootstrapFormValues) => Promise<SubmitResult>;
};

const SIGNAL_OPTIONS: Array<{ value: WorkflowBootstrapSignalType; label: string }> = [
  { value: "missed_check_in", label: "Missed check-in" },
  { value: "symptom_score", label: "Symptom score" },
  { value: "blood_pressure_systolic", label: "Blood pressure (systolic)" },
  { value: "blood_pressure_diastolic", label: "Blood pressure (diastolic)" },
  { value: "weight_change", label: "Weight change" },
];

const SEVERITY_OPTIONS: Array<{ value: WorkflowBootstrapEscalationSeverity; label: string }> = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

const PRIORITY_OPTIONS: Array<{ value: InterventionTaskPriority; label: string }> = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

const createDefaultValues = (): WorkflowBootstrapFormValues => ({
  firstName: "",
  lastName: "",
  dateOfBirth: "",
  signalType: "missed_check_in",
  signalNotes: "",
  escalationSeverity: "medium",
  createOpenTask: true,
  taskTitle: "Follow up with patient",
  taskDescription: "",
  taskPriority: "medium",
  taskDueAt: null,
});

const successPanelStyle: React.CSSProperties = {
  marginTop: "1.25rem",
  padding: "1.25rem",
  borderRadius: "14px",
  border: "1px solid #cbd5f5",
  backgroundColor: "#f0f5ff",
  display: "flex",
  flexDirection: "column",
  gap: "0.5rem",
};

const successStatsStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
  gap: "0.75rem",
};

export default function WorkflowBootstrapForm({ onSubmit }: Props) {
  const [values, setValues] = useState<WorkflowBootstrapFormValues>(createDefaultValues);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<SubmitResult | null>(null);

  const showTaskFields = values.createOpenTask;

  const isSubmitDisabled = useMemo(() => {
    if (isSubmitting) {
      return true;
    }
    if (!values.firstName.trim() || !values.lastName.trim() || !values.dateOfBirth) {
      return true;
    }
    if (showTaskFields && !values.taskTitle?.trim()) {
      return true;
    }
    return false;
  }, [isSubmitting, showTaskFields, values]);

  const setField = <K extends keyof WorkflowBootstrapFormValues>(
    key: K,
    value: WorkflowBootstrapFormValues[K],
  ) => {
    setValues((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitDisabled) {
      return;
    }
    setIsSubmitting(true);
    setResult(null);
    try {
      const normalizedValues: WorkflowBootstrapFormValues = {
        ...values,
        firstName: values.firstName.trim(),
        lastName: values.lastName.trim(),
        signalNotes: values.signalNotes?.trim(),
        taskTitle: values.taskTitle?.trim(),
        taskDescription: values.taskDescription?.trim(),
      };
      const outcome = await onSubmit(normalizedValues);
      setResult(outcome);
      if (outcome.success) {
        setValues((prev) => ({
          ...prev,
          firstName: "",
          lastName: "",
          dateOfBirth: "",
          signalNotes: "",
          taskDescription: "",
          taskDueAt: null,
        }));
      }
    } catch (error) {
      setResult({
        success: false,
        message: "Unable to create workflow bootstrap. Please retry.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="form-stack" onSubmit={handleSubmit} data-testid="workflow-bootstrap-form">
      <div className="form-field">
        <label htmlFor="first-name">First name</label>
        <input
          id="first-name"
          className="form-control"
          type="text"
          data-testid="workflow-bootstrap-first-name"
          value={values.firstName}
          onChange={(event) => setField("firstName", event.target.value)}
          disabled={isSubmitting}
          required
        />
      </div>
      <div className="form-field">
        <label htmlFor="last-name">Last name</label>
        <input
          id="last-name"
          className="form-control"
          type="text"
          data-testid="workflow-bootstrap-last-name"
          value={values.lastName}
          onChange={(event) => setField("lastName", event.target.value)}
          disabled={isSubmitting}
          required
        />
      </div>
      <div className="form-grid">
        <div className="form-field">
          <label htmlFor="date-of-birth">Date of birth</label>
          <input
            id="date-of-birth"
            className="form-control"
            type="date"
            data-testid="workflow-bootstrap-date-of-birth"
            value={values.dateOfBirth}
            onChange={(event) => setField("dateOfBirth", event.target.value)}
            disabled={isSubmitting}
            required
          />
        </div>
        <div className="form-field">
          <label htmlFor="signal-type">Signal type</label>
          <select
            id="signal-type"
            className="form-control"
            data-testid="workflow-bootstrap-signal-type"
            value={values.signalType}
            disabled={isSubmitting}
            onChange={(event) => setField("signalType", event.target.value as WorkflowBootstrapSignalType)}
          >
            {SIGNAL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label htmlFor="escalation-severity">Escalation severity</label>
          <select
            id="escalation-severity"
            className="form-control"
            data-testid="workflow-bootstrap-escalation-severity"
            value={values.escalationSeverity}
            disabled={isSubmitting}
            onChange={(event) =>
              setField("escalationSeverity", event.target.value as WorkflowBootstrapEscalationSeverity)
            }
          >
            {SEVERITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="form-field">
        <label htmlFor="signal-notes">Signal note (optional)</label>
        <textarea
          id="signal-notes"
          className="form-control"
          data-testid="workflow-bootstrap-signal-notes"
          rows={2}
          value={values.signalNotes ?? ""}
          disabled={isSubmitting}
          placeholder="Add any quick context for the generated workflow case"
          onChange={(event) => setField("signalNotes", event.target.value)}
        />
      </div>
      <div className="form-field">
        <label>
          <input
            type="checkbox"
            data-testid="workflow-bootstrap-create-open-task"
            checked={values.createOpenTask}
            disabled={isSubmitting}
            onChange={(event) => setField("createOpenTask", event.target.checked)}
          />{" "}
          Create an open task
        </label>
        <p className="inline-helper">Uncheck to skip task creation.</p>
      </div>
      {showTaskFields ? (
        <>
          <div className="form-field">
            <label htmlFor="task-title">Task title</label>
            <input
              id="task-title"
              className="form-control"
              type="text"
              data-testid="workflow-bootstrap-task-title"
              value={values.taskTitle ?? ""}
              disabled={isSubmitting}
              placeholder="Example: Call patient to review escalated signal"
              onChange={(event) => setField("taskTitle", event.target.value)}
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="task-description">Task notes (optional)</label>
            <textarea
              id="task-description"
              className="form-control"
              data-testid="workflow-bootstrap-task-description"
              rows={2}
              value={values.taskDescription ?? ""}
              disabled={isSubmitting}
              onChange={(event) => setField("taskDescription", event.target.value)}
              placeholder="Short operator instructions"
            />
          </div>
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="task-priority">Task priority</label>
              <select
                id="task-priority"
                className="form-control"
                data-testid="workflow-bootstrap-task-priority"
                value={values.taskPriority}
                disabled={isSubmitting}
                onChange={(event) => setField("taskPriority", event.target.value as InterventionTaskPriority)}
              >
                {PRIORITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label htmlFor="task-due-at">Task due by (optional)</label>
              <input
                id="task-due-at"
                className="form-control"
                type="datetime-local"
                value={values.taskDueAt ?? ""}
                disabled={isSubmitting}
                onChange={(event) => setField("taskDueAt", event.target.value || null)}
              />
            </div>
          </div>
        </>
      ) : null}
      <div className="form-footer">
        <button type="submit" className="button button--primary" disabled={isSubmitDisabled}>
          {isSubmitting ? "Creating…" : "Create workflow bootstrap"}
        </button>
      </div>
      {result && !result.success ? (
        <p className="form-feedback form-feedback--error">
          {result.message ?? "Unable to create workflow bootstrap."}
        </p>
      ) : null}
      {result?.success && result.response ? (
        <div style={successPanelStyle} aria-live="polite" data-testid="workflow-bootstrap-success">
          <p className="inline-helper">
            Workflow bootstrap created for <strong>{result.response.patient_full_name}</strong>.
          </p>
          <div style={successStatsStyle}>
            <div>
              <p className="eyebrow">Patient ID</p>
              <p>
                <code>{result.response.patient_id}</code>
              </p>
            </div>
            <div>
              <p className="eyebrow">Signal ID</p>
              <p>
                <code>{result.response.signal_id}</code>
              </p>
            </div>
            <div>
              <p className="eyebrow">Escalation ID</p>
              <p>
                <code>{result.response.escalation_id}</code>
              </p>
            </div>
            <div>
              <p className="eyebrow">Task ID</p>
              <p>
                <code>
                  {result.response.task_id ?? (result.response.task_created ? "Created" : "Not created")}
                </code>
              </p>
            </div>
          </div>
          <div>
            <Link href={`/patients/${result.response.patient_id}`} className="button button--ghost">
              Open patient detail
            </Link>
          </div>
        </div>
      ) : null}
    </form>
  );
}
