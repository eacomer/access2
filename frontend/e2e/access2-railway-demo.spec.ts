import { expect, test, type Page } from "@playwright/test";

import {
  apiPatch,
  exportAuditBundle,
  findDemoPatientCandidate,
  getApiToken,
  getPatientAuditStatus,
  getSnapshot,
  getSnapshotEvents,
  login,
  verifyAuditManifest,
} from "./helpers/access2";

const REJECTION_REASON =
  "Outcome documentation does not clearly connect intervention to measurable improvement.";

const OVERRIDE_REASON =
  "Approved for demo exception: source documentation exists outside the synthetic dataset and will be reconciled before production use.";

async function expectEvidenceChainPanel(page: Page, expectedPostureText: RegExp[]) {
  const panel = page.getByTestId("patient-evidence-chain-panel");

  await expect(panel).toBeVisible();
  await expect(panel).toContainText("Evidence chain");
  await expect(panel).toContainText("Proof path");
  await expect(panel).toContainText(
    "Shows whether this patient has the proof chain needed to connect interventions to measurable outcomes.",
  );

  const expectedRows = [
    "Signal",
    "Escalation",
    "Intervention",
    "Outcome",
    "Evidence",
    "Case Summary",
    "Review Packet",
    "Review State",
    "Audit Bundle",
  ];
  for (const label of expectedRows) {
    await expect(panel).toContainText(label);
  }

  for (const postureText of expectedPostureText) {
    await expect(panel).toContainText(postureText);
  }

  await expect(panel.getByRole("button")).toHaveCount(0);
  await expect(panel.getByRole("link")).toHaveCount(0);
}

async function expectManifestVerificationPanel(page: Page, expectedPostureText: RegExp[]) {
  const panel = page.getByTestId("patient-manifest-verification-panel");

  await expect(panel).toBeVisible();
  await expect(panel).toContainText("Manifest verification");
  await expect(panel).toContainText("Audit bundle verification posture");
  await expect(panel).toContainText(
    "Shows whether the persisted review packet and audit bundle posture can support verification without changing workflow state.",
  );

  const expectedRows = [
    "Review Packet Snapshot",
    "Review State",
    "Audit Bundle",
    "Export Status",
    "Export Formats",
    "Manifest Verification",
  ];
  for (const label of expectedRows) {
    await expect(panel).toContainText(label);
  }

  for (const postureText of expectedPostureText) {
    await expect(panel).toContainText(postureText);
  }

  await expect(panel.getByRole("button")).toHaveCount(0);
  await expect(panel.getByRole("link")).toHaveCount(0);
}

test.describe("ACCESS2 Railway synthetic demo cases", () => {
  test("can log into the deployed ACCESS2 frontend", async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Patients" }).click();
    await expect(page.getByRole("heading", { name: "Patient queue" })).toBeVisible();
  });

  test("Demo Patient 2 - Missing Evidence", async ({ page, request }) => {
    await login(page);
    const token = await getApiToken(request);
    const patient = await findDemoPatientCandidate(request, token, {
      label: "Demo Patient 2",
      patientIdEnv: "ACCESS2_E2E_DEMO_PATIENT_2_ID",
      matchesAuditStatus: (auditStatus) =>
        !auditStatus.completion_summary.has_required_evidence &&
        auditStatus.completion_summary.missing_evidence_count > 0,
    });
    if (!patient) {
      test.skip(true, "Demo Patient 2 synthetic data is not present in this environment.");
      return;
    }

    const auditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
    expect(patient.total_events).toBeGreaterThan(0);
    expect(patient.latest_open_escalation_id).toBeTruthy();
    expect(patient.task_summary?.open_task_count || patient.task_summary?.in_progress_task_count || 0).toBeGreaterThan(0);
    expect(auditStatus.completion_summary.has_required_evidence).toBe(false);
    expect(auditStatus.completion_summary.missing_evidence_count).toBeGreaterThan(0);
    expect(auditStatus.audit_bundle.available).toBe(false);
    expect(auditStatus.next_step.action).toMatch(/complete_missing_evidence|create_snapshot|review_snapshot/);

    await page.goto(`/patients/${patient.patient_id}`);
    await expectEvidenceChainPanel(page, [/Evidence\s*Missing/i, /Audit Bundle\s*Export not available/i]);
    await expectManifestVerificationPanel(page, [
      /Review State\s*Pending Review/i,
      /Audit Bundle\s*Unavailable/i,
      /Manifest Verification\s*Verification unavailable/i,
      /Review packet approval is required/i,
    ]);
    await expect(page.getByTestId("patient-audit-status-panel")).toContainText("Audit bundle available");
    await expect(page.getByTestId("patient-audit-status-panel")).toContainText("No");
    await expect(page.getByTestId("patient-audit-status-panel")).toContainText(/missing|required|snapshot/i);

    if (auditStatus.latest_snapshot_id && auditStatus.review_status === "pending_review") {
      const approvalAttempt = await apiPatch(
        request,
        token,
        `/reports/access-review-packet/snapshots/${auditStatus.latest_snapshot_id}/review`,
        {
          review_status: "approved",
          review_note: "Normal approval should remain blocked for missing evidence.",
        },
      );
      expect(approvalAttempt.status()).toBe(409);
      expect(await approvalAttempt.text()).toMatch(/missing|required|blocked/i);
    } else {
      test.info().annotations.push({
        type: "product gap",
        description:
          "Normal approval blocking is verified only when the seeded missing-evidence case has a pending snapshot; this environment exposes no safe pending snapshot to patch.",
      });
    }
  });

  test("Demo Patient 1 - Audit Ready", async ({ page, request }) => {
    await login(page);
    const token = await getApiToken(request);
    const patient = await findDemoPatientCandidate(request, token, {
      label: "Demo Patient 1",
      patientIdEnv: "ACCESS2_E2E_DEMO_PATIENT_1_ID",
      matchesAuditStatus: (auditStatus) =>
        auditStatus.review_status === "approved" &&
        auditStatus.completion_summary.has_required_evidence &&
        auditStatus.audit_bundle.available,
    });
    if (!patient) {
      test.skip(true, "Demo Patient 1 synthetic data is not present in this environment.");
      return;
    }

    const auditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
    expect(patient.total_events).toBeGreaterThan(0);
    expect(patient.latest_open_escalation_id || patient.workflow_status).toBeTruthy();
    expect(auditStatus.has_snapshot).toBe(true);
    expect(auditStatus.review_status).toBe("approved");
    expect(auditStatus.completion_summary.has_required_evidence).toBe(true);
    expect(auditStatus.completion_summary.has_approval).toBe(true);
    expect(auditStatus.audit_bundle.available).toBe(true);
    expect(auditStatus.latest_snapshot_id).toBeTruthy();

    const snapshotId = auditStatus.latest_snapshot_id as string;
    const bundle = await exportAuditBundle(request, token, snapshotId);
    expect(bundle.audit_manifest.snapshot_id).toBe(snapshotId);
    expect(bundle.audit_manifest.patient_id).toBe(patient.patient_id);

    const verification = await verifyAuditManifest(request, token, snapshotId, bundle.audit_manifest);
    expect(verification.verified).toBe(true);
    expect(verification.mismatches).toEqual([]);

    await page.goto(`/patients/${patient.patient_id}`);
    await expectEvidenceChainPanel(page, [
      /Evidence\s*Complete/i,
      /Review State\s*Complete/i,
      /Audit Bundle\s*(Export available|Complete)/i,
    ]);
    await expectManifestVerificationPanel(page, [
      /Review State\s*Approved/i,
      /Audit Bundle\s*Available/i,
      /Export Status\s*Exported/i,
      /Manifest Verification\s*Verification-ready/i,
    ]);
    await expect(page.getByTestId("patient-review-packet-backlog-panel")).toContainText("Download JSON");
    const frontendBundle = await page.request.get(`/audit-bundles/${snapshotId}/json`);
    expect(frontendBundle.ok(), await frontendBundle.text()).toBeTruthy();

    await page.goto("/audit-bundle-verify");
    await page.getByLabel("Snapshot ID").fill(snapshotId);
    await page.getByLabel("Audit manifest JSON").fill(JSON.stringify(bundle.audit_manifest, null, 2));
    await page.getByRole("button", { name: "Verify Manifest" }).click();
    await expect(page.getByText("Verified", { exact: true })).toBeVisible();
  });

  test("Demo Patient 3 - Rejected Review", async ({ page, request }) => {
    await login(page);
    const token = await getApiToken(request);
    const patient = await findDemoPatientCandidate(request, token, {
      label: "Demo Patient 3",
      patientIdEnv: "ACCESS2_E2E_DEMO_PATIENT_3_ID",
      matchesAuditStatus: (auditStatus) => auditStatus.review_status === "rejected",
    });
    if (!patient) {
      test.skip(true, "Demo Patient 3 synthetic data is not present in this environment.");
      return;
    }

    const auditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
    expect(auditStatus.review_status).toBe("rejected");
    expect(auditStatus.next_step.action).toBe("create_snapshot");
    expect(auditStatus.latest_snapshot_id).toBeTruthy();

    const snapshotId = auditStatus.latest_snapshot_id as string;
    const before = await getSnapshot(request, token, snapshotId);
    expect(before.review_status).toBe("rejected");
    const events = await getSnapshotEvents(request, token, snapshotId);
    expect(JSON.stringify(events)).toContain(REJECTION_REASON);
    const after = await getSnapshot(request, token, snapshotId);
    expect(after.packet_json).toEqual(before.packet_json);
    expect(after.packet_markdown).toEqual(before.packet_markdown);

    await page.goto(`/patients/${patient.patient_id}`);
    await expectEvidenceChainPanel(page, [
      /Review State\s*Review rejected/i,
      /Audit Bundle\s*Export not available/i,
    ]);
    await expectManifestVerificationPanel(page, [
      /Review State\s*Rejected/i,
      /Audit Bundle\s*Unavailable/i,
      /Manifest Verification\s*Verification unavailable/i,
      /latest review packet was rejected/i,
    ]);
    await expect(page.getByTestId("patient-review-packet-backlog-panel")).toContainText("Rejected");
    await expect(page.getByTestId("patient-review-packet-backlog-panel")).toContainText(
      "Unavailable for rejected snapshots.",
    );
  });

  test("Demo Patient 4 - Override Approval", async ({ page, request }) => {
    await login(page);
    const token = await getApiToken(request);
    const patient = await findDemoPatientCandidate(request, token, {
      label: "Demo Patient 4",
      patientIdEnv: "ACCESS2_E2E_DEMO_PATIENT_4_ID",
      matchesAuditStatus: (auditStatus) =>
        auditStatus.review_status === "approved" &&
        Boolean(auditStatus.review_state?.approval_override_used),
    });
    if (!patient) {
      test.skip(true, "Demo Patient 4 synthetic data is not present in this environment.");
      return;
    }

    const auditStatus = await getPatientAuditStatus(request, token, patient.patient_id);
    expect(auditStatus.review_status).toBe("approved");
    expect(auditStatus.review_state?.approval_override_used).toBe(true);
    expect(auditStatus.audit_bundle.available).toBe(true);
    expect(auditStatus.latest_snapshot_id).toBeTruthy();

    const snapshotId = auditStatus.latest_snapshot_id as string;
    const snapshot = await getSnapshot(request, token, snapshotId);
    expect(snapshot.review_state?.approval_override_used).toBe(true);
    const events = await getSnapshotEvents(request, token, snapshotId);
    expect(JSON.stringify(events)).toContain(OVERRIDE_REASON);

    const bundle = await exportAuditBundle(request, token, snapshotId);
    expect(bundle.audit_manifest.approval_override_used).toBe(true);
    const verification = await verifyAuditManifest(request, token, snapshotId, bundle.audit_manifest);
    expect(verification.verified).toBe(true);
    expect(verification.mismatches).toEqual([]);

    await page.goto(`/patients/${patient.patient_id}`);
    await expectEvidenceChainPanel(page, [
      /Review State\s*Approved With Override/i,
      /Audit Bundle\s*(Export available|Complete)/i,
    ]);
    await expectManifestVerificationPanel(page, [
      /Review State\s*Approved With Override/i,
      /Audit Bundle\s*Available/i,
      /Manifest Verification\s*Verification-ready/i,
    ]);
    await expect(page.getByTestId("patient-audit-status-panel")).toContainText(/Approved With Override/i);
  });

  test("Demo Patient 3 reviewer rejection through UI", async () => {
    test.skip(
      true,
      "Current frontend read-only audit panels do not expose reject controls; rejection is verified through existing backend snapshot/event state.",
    );
  });

  test("Demo Patient 4 superuser override approval through UI", async () => {
    test.skip(
      true,
      "Current frontend read-only audit panels do not expose approval override controls; override metadata is verified through existing backend snapshot/event/bundle state.",
    );
  });
});
