import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import {
  apiGet,
  apiPost,
  findLocalV2RejectionMutationPatient,
  getApiBaseUrl,
  getApiToken,
  getCurrentUser,
  getPatientAuditStatus,
  getSnapshot,
  getSnapshotEvents,
  LOCAL_V2_REJECTION_MUTATION_MARKER,
  login,
} from "./helpers/access2";

const ENABLE_LOCAL_MUTATION_ENV = "ACCESS2_ENABLE_LOCAL_MUTATION_E2E";
const LOCAL_MUTATION_REASON =
  "Synthetic local V2 rejection mutation test reason: outcome evidence needs correction.";
const POST_REJECTION_CORRECTION_CARE_SUMMARY =
  "Post-rejection corrected evidence: synthetic systolic BP outcome improved after the completed intervention.";
const POST_REJECTION_CORRECTION_OUTCOME_SOURCE = "access2_local_v2_post_rejection_correction";
const POST_REJECTION_CORRECTION_OUTCOME_VALUE = 124;
const PRODUCTION_HOST_MARKERS = [
  "access2.salvardata.com",
  "api.salvardata.com",
  "railway.app",
  "up.railway.app",
];

const localMutationEnabled = process.env[ENABLE_LOCAL_MUTATION_ENV]?.trim().toLowerCase() === "true";

type InterventionTask = {
  id: string;
  escalation_id: string | null;
  status: string;
};

type OutcomeResponse = {
  id: string;
};

function assertSafeLocalTargets() {
  const targets = [
    process.env.ACCESS2_E2E_BASE_URL || "http://localhost:3000",
    process.env.ACCESS2_E2E_API_BASE_URL || getApiBaseUrl(),
  ];

  const productionLikeTarget = targets.find((target) =>
    PRODUCTION_HOST_MARKERS.some((marker) => target.toLowerCase().includes(marker)),
  );
  if (productionLikeTarget) {
    throw new Error(
      `Refusing to run local mutation E2E against production/Railway-like target: ${productionLikeTarget}`,
    );
  }
}

async function createPostRejectionCorrectionEvidence({
  patientId,
  request,
  token,
}: {
  patientId: string;
  request: APIRequestContext;
  token: string;
}) {
  const tasks = await apiGet<InterventionTask[]>(request, token, `/patients/${patientId}/tasks`);
  const completedTask = tasks.find((task) => task.status === "completed") ?? tasks[0];
  expect(completedTask, "Local mutation patient needs an intervention task.").toBeTruthy();

  const observedAt = new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString();
  const correctedOutcome = await apiPost<OutcomeResponse>(request, token, "/outcomes", {
    patient_id: patientId,
    intervention_task_id: completedTask.id,
    type: "bp",
    metric_name: "systolic_bp",
    value_numeric: POST_REJECTION_CORRECTION_OUTCOME_VALUE,
    unit: "mmHg",
    observed_at: observedAt,
    source: POST_REJECTION_CORRECTION_OUTCOME_SOURCE,
  });

  await apiPost(request, token, `/patients/${patientId}/care-updates`, {
    patient_id: patientId,
    summary: POST_REJECTION_CORRECTION_CARE_SUMMARY,
    details: "Synthetic local V2 correction evidence for disposable mutation testing. No real PHI.",
    care_update_type: "follow_up",
    occurred_at: new Date(Date.now() + 49 * 60 * 60 * 1000).toISOString(),
    escalation_id: completedTask.escalation_id,
    intervention_task_id: completedTask.id,
    outcome_id: correctedOutcome.id,
  });
}

async function openPatientBacklog(page: Page, patientId: string) {
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    await page.goto(`/patients/${patientId}`);
    const backlogPanel = page.getByTestId("patient-review-packet-backlog-panel");
    try {
      await expect(backlogPanel).toBeVisible({ timeout: 30_000 });
      return backlogPanel;
    } catch (error) {
      if (attempt === 3) {
        throw error;
      }
      await page.waitForTimeout(1_000);
    }
  }
  throw new Error("Patient review packet backlog did not load.");
}

test.describe.serial("ACCESS2 local V2 reviewer assignment, rejection, new snapshot, and approval mutation", () => {
  test.skip(
    !localMutationEnabled,
    `${ENABLE_LOCAL_MUTATION_ENV}=true is required to run local mutation E2E.`,
  );

  test.beforeAll(() => {
    assertSafeLocalTargets();
  });

  test("assigns, rejects, creates, and approves a corrected disposable local snapshot through the patient UI", async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);
    await login(page);
    const token = await getApiToken(request);
    const currentUser = await getCurrentUser(request, token);
    const patient = await findLocalV2RejectionMutationPatient(request, token);
    if (!patient) {
      test.skip(
        true,
        `Local mutation patient ${LOCAL_V2_REJECTION_MUTATION_MARKER} is not present; run backend/scripts/seed_local_v2_rejection_mutation.py first.`,
      );
      return;
    }

    const beforeAuditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
    expect(beforeAuditStatus.review_status).toBe("pending_review");
    expect(beforeAuditStatus.latest_snapshot_id).toBeTruthy();
    expect(beforeAuditStatus.audit_bundle.available).toBe(false);

    const snapshotId = beforeAuditStatus.latest_snapshot_id as string;
    const beforeSnapshot = await getSnapshot(request, token, snapshotId);
    expect(beforeSnapshot.review_status).toBe("pending_review");
    expect(beforeSnapshot.packet_json).toBeTruthy();
    expect(beforeSnapshot.packet_markdown).toBeTruthy();

    let backlogPanel = await openPatientBacklog(page, patient.patient_id);
    await expect(backlogPanel).toContainText("Pending Review");
    await expect(backlogPanel).toContainText("Unavailable until the snapshot is approved and export-ready.");

    const assignmentControls = backlogPanel.getByTestId("reviewer-assignment-control");
    await expect(assignmentControls).toHaveCount(1);
    const assignmentControl = assignmentControls.first();
    await expect(assignmentControl).toBeVisible();
    await expect(assignmentControl).toContainText("V2 controlled reviewer assignment");

    await assignmentControl.getByRole("button", { name: "Assign reviewer" }).click();
    await expect(assignmentControl.getByRole("alert")).toContainText("Reviewer user ID required.");

    const assignmentResponsePromise = page.waitForResponse((response) => {
      const method = response.request().method();
      return (
        response.url().includes("/review-packet-snapshots/") &&
        response.url().includes("/assignment") &&
        ["POST", "PATCH", "PUT"].includes(method)
      );
    });

    await assignmentControl.getByLabel("V2 controlled reviewer assignment").fill(currentUser.id);
    await assignmentControl.getByRole("button", { name: "Assign reviewer" }).click();

    const assignmentResponse = await assignmentResponsePromise;
    expect(assignmentResponse.ok(), await assignmentResponse.text()).toBeTruthy();
    await expect(assignmentControl.getByRole("alert")).toHaveCount(0);

    await expect
      .poll(async () => {
        const assignedSnapshot = await getSnapshot(request, token, snapshotId);
        return assignedSnapshot.assigned_reviewer_user_id;
      }, { timeout: 30_000 })
      .toBe(currentUser.id);

    const assignedSnapshot = await getSnapshot(request, token, snapshotId);
    expect(assignedSnapshot.review_status).toBe("pending_review");
    expect(assignedSnapshot.packet_json).toEqual(beforeSnapshot.packet_json);
    expect(assignedSnapshot.packet_markdown).toEqual(beforeSnapshot.packet_markdown);

    const rejectionControls = backlogPanel.getByTestId("reviewer-rejection-control");
    await expect(rejectionControls).toHaveCount(1);
    const rejectionControl = rejectionControls.first();
    await expect(rejectionControl).toBeVisible();
    await expect(rejectionControl).toContainText("V2 controlled reviewer rejection");

    await rejectionControl.getByRole("button", { name: "Reject snapshot" }).click();
    await expect(rejectionControl.getByRole("alert")).toContainText("Rejection reason required.");

    await rejectionControl.getByLabel("V2 controlled reviewer rejection").fill(LOCAL_MUTATION_REASON);
    await rejectionControl.getByRole("button", { name: "Reject snapshot" }).click();

    await expect
      .poll(async () => {
        const auditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
        return auditStatus.review_status;
      }, { timeout: 30_000 })
      .toBe("rejected");

    backlogPanel = await openPatientBacklog(page, patient.patient_id);

    await expect(backlogPanel).toContainText("Rejected", { timeout: 30_000 });
    await expect(backlogPanel).toContainText("Unavailable for rejected snapshots.");
    await expect(backlogPanel.getByRole("button", { name: "Assign reviewer" })).toHaveCount(0);
    await expect(backlogPanel.getByRole("button", { name: "Reject snapshot" })).toHaveCount(0);

    const afterAuditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
    expect(afterAuditStatus.latest_snapshot_id).toBe(snapshotId);
    expect(afterAuditStatus.next_step.action).toBe("create_snapshot");
    expect(afterAuditStatus.audit_bundle.available).toBe(false);

    const afterSnapshot = await getSnapshot(request, token, snapshotId);
    expect(afterSnapshot.review_status).toBe("rejected");
    expect(afterSnapshot.assigned_reviewer_user_id).toBe(currentUser.id);
    expect(afterSnapshot.packet_json).toEqual(beforeSnapshot.packet_json);
    expect(afterSnapshot.packet_markdown).toEqual(beforeSnapshot.packet_markdown);

    const events = await getSnapshotEvents(request, token, snapshotId);
    expect(JSON.stringify(events)).toContain("snapshot_assigned");
    expect(JSON.stringify(events)).toContain(currentUser.id);
    expect(JSON.stringify(events)).toContain("snapshot_rejected");
    expect(JSON.stringify(events)).toContain(LOCAL_MUTATION_REASON);

    const rejectedBundle = await request.get(
      `${getApiBaseUrl()}/reports/access-review-packet/snapshots/${snapshotId}/audit-bundle`,
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    expect(rejectedBundle.status()).toBe(409);
    expect(await rejectedBundle.text()).toMatch(/rejected|approved/i);

    await createPostRejectionCorrectionEvidence({
      patientId: patient.patient_id,
      request,
      token,
    });

    const createControls = backlogPanel.getByTestId("review-packet-snapshot-create-control");
    await expect(createControls).toHaveCount(1);
    const createControl = createControls.first();
    await expect(createControl).toContainText("Existing packet JSON and Markdown stay preserved.");
    await createControl.getByRole("button", { name: "Create new review packet snapshot" }).click();
    await expect(createControl.getByRole("status")).toContainText("New review packet snapshot created.", {
      timeout: 30_000,
    });

    await expect
      .poll(async () => {
        const auditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
        return auditStatus.latest_snapshot_id;
      }, { timeout: 30_000 })
      .not.toBe(snapshotId);

    const refreshedAuditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
    expect(refreshedAuditStatus.review_status).toBe("pending_review");
    expect(refreshedAuditStatus.latest_snapshot_id).toBeTruthy();
    expect(refreshedAuditStatus.latest_snapshot_id).not.toBe(snapshotId);
    expect(refreshedAuditStatus.audit_bundle.available).toBe(false);

    const newSnapshotId = refreshedAuditStatus.latest_snapshot_id as string;
    const newSnapshot = await getSnapshot(request, token, newSnapshotId);
    expect(newSnapshot.review_status).toBe("pending_review");
    expect(newSnapshot.packet_json).toBeTruthy();
    expect(newSnapshot.packet_markdown).toBeTruthy();
    expect(newSnapshot.packet_markdown).toContain(POST_REJECTION_CORRECTION_CARE_SUMMARY);
    expect(newSnapshot.packet_markdown).toContain("status=improved");

    const oldRejectedSnapshot = await getSnapshot(request, token, snapshotId);
    expect(oldRejectedSnapshot.review_status).toBe("rejected");
    expect(oldRejectedSnapshot.packet_json).toEqual(beforeSnapshot.packet_json);
    expect(oldRejectedSnapshot.packet_markdown).toEqual(beforeSnapshot.packet_markdown);

    backlogPanel = await openPatientBacklog(page, patient.patient_id);
    await expect(backlogPanel).toContainText("Pending Review", { timeout: 30_000 });
    await expect(backlogPanel).toContainText("Rejected");
    await expect(backlogPanel.getByTestId("review-packet-snapshot-create-control")).toHaveCount(0);
    await expect(backlogPanel.getByRole("button", { name: "Assign reviewer" })).toHaveCount(1);
    await expect(backlogPanel.getByRole("button", { name: "Reject snapshot" })).toHaveCount(1);
    await expect(backlogPanel.getByRole("button", { name: "Approve snapshot" })).toHaveCount(1);
    await expect(backlogPanel).toContainText("Read-only for this snapshot.");

    const newEvents = await getSnapshotEvents(request, token, newSnapshotId);
    expect(JSON.stringify(newEvents)).toContain("snapshot_created");

    const approvalControl = backlogPanel.getByTestId("review-packet-snapshot-approval-control").first();
    await expect(approvalControl).toContainText(
      "Approves the latest pending packet only when the persisted review checklist has no missing evidence.",
    );
    await approvalControl.getByRole("button", { name: "Approve snapshot" }).click();
    await expect(approvalControl.getByRole("status")).toContainText("Review packet snapshot approved.", {
      timeout: 30_000,
    });

    await expect
      .poll(async () => {
        const auditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
        return auditStatus.review_status;
      }, { timeout: 30_000 })
      .toBe("approved");

    const approvedAuditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
    expect(approvedAuditStatus.latest_snapshot_id).toBe(newSnapshotId);
    expect(approvedAuditStatus.audit_bundle.available).toBe(true);

    const approvedSnapshot = await getSnapshot(request, token, newSnapshotId);
    expect(approvedSnapshot.review_status).toBe("approved");
    expect(approvedSnapshot.packet_json).toEqual(newSnapshot.packet_json);
    expect(approvedSnapshot.packet_markdown).toEqual(newSnapshot.packet_markdown);

    const approvedEvents = await getSnapshotEvents(request, token, newSnapshotId);
    expect(JSON.stringify(approvedEvents)).toContain("snapshot_approved");

    backlogPanel = await openPatientBacklog(page, patient.patient_id);
    await expect(backlogPanel).toContainText("Approved", { timeout: 30_000 });
    await expect(backlogPanel).toContainText("Rejected");
    await expect(backlogPanel.getByRole("button", { name: "Assign reviewer" })).toHaveCount(0);
    await expect(backlogPanel.getByRole("button", { name: "Reject snapshot" })).toHaveCount(0);
    await expect(backlogPanel.getByRole("button", { name: "Approve snapshot" })).toHaveCount(0);
    await expect(backlogPanel.getByRole("button", { name: "Create new review packet snapshot" })).toHaveCount(0);
    await expect
      .poll(async () => backlogPanel.getByText("Read-only for this snapshot.").count(), { timeout: 30_000 })
      .toBeGreaterThanOrEqual(2);

    await page.goto("/audit-readiness");
    const auditReadinessPage = page.getByTestId("audit-readiness-page");
    await expect(auditReadinessPage).toBeVisible();
    await expect(auditReadinessPage).toContainText("Read-only V1 queue");
    await expect(
      auditReadinessPage.getByRole("button", { name: /approve|reject|assign|override|export|create snapshot/i }),
    ).toHaveCount(0);
  });
});
