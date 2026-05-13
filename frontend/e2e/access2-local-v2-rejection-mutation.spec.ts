import { expect, test } from "@playwright/test";

import {
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
const PRODUCTION_HOST_MARKERS = [
  "access2.salvardata.com",
  "api.salvardata.com",
  "railway.app",
  "up.railway.app",
];

const localMutationEnabled = process.env[ENABLE_LOCAL_MUTATION_ENV]?.trim().toLowerCase() === "true";

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

test.describe.serial("ACCESS2 local V2 reviewer assignment, rejection, and new snapshot mutation", () => {
  test.skip(
    !localMutationEnabled,
    `${ENABLE_LOCAL_MUTATION_ENV}=true is required to run local mutation E2E.`,
  );

  test.beforeAll(() => {
    assertSafeLocalTargets();
  });

  test("assigns, rejects, and creates a new disposable local pending-review snapshot through the patient UI", async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);
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

    await page.goto(`/patients/${patient.patient_id}`);
    const backlogPanel = page.getByTestId("patient-review-packet-backlog-panel");
    await expect(backlogPanel).toBeVisible();
    await expect(backlogPanel).toContainText("Pending Review");
    await expect(backlogPanel).toContainText("Unavailable until the snapshot is approved and export-ready.");

    const assignmentControls = backlogPanel.getByTestId("reviewer-assignment-control");
    await expect(assignmentControls).toHaveCount(1);
    const assignmentControl = assignmentControls.first();
    await expect(assignmentControl).toBeVisible();
    await expect(assignmentControl).toContainText("V2 controlled reviewer assignment");

    await assignmentControl.getByRole("button", { name: "Assign reviewer" }).click();
    await expect(assignmentControl.getByRole("alert")).toContainText("Reviewer user ID required.");

    await assignmentControl.getByLabel("V2 controlled reviewer assignment").fill(currentUser.id);
    await assignmentControl.getByRole("button", { name: "Assign reviewer" }).click();
    await expect(assignmentControl.getByRole("status")).toContainText("Reviewer assigned.", {
      timeout: 30_000,
    });
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

    const oldRejectedSnapshot = await getSnapshot(request, token, snapshotId);
    expect(oldRejectedSnapshot.review_status).toBe("rejected");
    expect(oldRejectedSnapshot.packet_json).toEqual(beforeSnapshot.packet_json);
    expect(oldRejectedSnapshot.packet_markdown).toEqual(beforeSnapshot.packet_markdown);

    await expect(backlogPanel).toContainText("Pending Review", { timeout: 30_000 });
    await expect(backlogPanel).toContainText("Rejected");
    await expect(createControls).toHaveCount(0);
    await expect(backlogPanel.getByRole("button", { name: "Assign reviewer" })).toHaveCount(1);
    await expect(backlogPanel.getByRole("button", { name: "Reject snapshot" })).toHaveCount(1);
    await expect(backlogPanel).toContainText("Read-only for this snapshot.");

    const newEvents = await getSnapshotEvents(request, token, newSnapshotId);
    expect(JSON.stringify(newEvents)).toContain("snapshot_created");

    await page.goto("/audit-readiness");
    const auditReadinessPage = page.getByTestId("audit-readiness-page");
    await expect(auditReadinessPage).toBeVisible();
    await expect(auditReadinessPage).toContainText("Read-only V1 queue");
    await expect(
      auditReadinessPage.getByRole("button", { name: /approve|reject|assign|override|export|create snapshot/i }),
    ).toHaveCount(0);
  });
});
