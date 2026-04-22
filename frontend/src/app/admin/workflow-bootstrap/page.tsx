import WorkflowBootstrapForm, {
  WorkflowBootstrapFormValues,
} from "../../../components/admin/WorkflowBootstrapForm";
import { createWorkflowBootstrap } from "../../../lib/api";
import { requireAuth } from "../../../lib/auth/session";
import type { WorkflowBootstrapCreateRequest } from "../../../types/admin";

const ADMIN_PAGE_PATH = "/admin/workflow-bootstrap";

export const dynamic = "force-dynamic";

export default async function WorkflowBootstrapPage() {
  await requireAuth(ADMIN_PAGE_PATH);

  const submitBootstrap = async (values: WorkflowBootstrapFormValues) => {
    "use server";

    const payload: WorkflowBootstrapCreateRequest = {
      scenario: values.scenario,
      first_name: values.firstName,
      last_name: values.lastName,
      date_of_birth: values.dateOfBirth,
      signal_type: values.signalType,
      signal_notes: values.signalNotes?.length ? values.signalNotes : null,
      signal_source: "frontend_admin_bootstrap",
      escalation_severity: values.escalationSeverity,
      escalation_type: "clinical_review",
      create_open_task: values.createOpenTask,
      task_title: values.createOpenTask ? values.taskTitle ?? null : null,
      task_description: values.createOpenTask ? values.taskDescription ?? null : null,
      task_priority: values.createOpenTask ? values.taskPriority : undefined,
      task_due_at:
        values.createOpenTask && values.taskDueAt
          ? new Date(values.taskDueAt).toISOString()
          : null,
      escalation_note: values.signalNotes?.length ? values.signalNotes : null,
    };

    try {
      const response = await createWorkflowBootstrap(payload, {
        authRedirectPath: ADMIN_PAGE_PATH,
      });
      return { success: true, response };
    } catch (error) {
      console.error("Failed to create workflow bootstrap", error);
      const message =
        error instanceof Error ? error.message : "Unable to create workflow bootstrap.";
      return { success: false, message };
    }
  };

  return (
    <main className="page" data-testid="workflow-bootstrap-page">
      <section className="section-card">
        <div className="section-header">
          <div>
            <p className="eyebrow">Admin utilities</p>
            <h1 className="section-title">Workflow bootstrap</h1>
            <p className="section-subtitle">
              Create fresh workflow cases for demo or QA without leaving the app.
            </p>
          </div>
        </div>
        <WorkflowBootstrapForm onSubmit={submitBootstrap} />
      </section>
    </main>
  );
}
