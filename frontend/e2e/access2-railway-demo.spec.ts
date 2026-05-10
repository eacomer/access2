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

async function expectOutcomeProofGapsPanel(page: Page, expectedPostureText: RegExp[]) {
  const panel = page.getByTestId("patient-outcome-proof-gaps-panel");

  await expect(panel).toBeVisible();
  await expect(panel).toContainText("Outcome proof");
  await expect(panel).toContainText("Outcome Proof Gaps");
  await expect(panel).toContainText(
    "Read-only proof checklist showing which outcome and evidence elements support audit readiness.",
  );

  const expectedRows = [
    "Signal",
    "Escalation",
    "Intervention",
    "Outcome",
    "Evidence",
    "Case Summary / Snapshot",
    "Review Posture",
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

function expectReadinessReasonShape(reasons: unknown) {
  expect(Array.isArray(reasons)).toBe(true);
  const reasonList = reasons as Array<Record<string, unknown>>;
  expect(reasonList.length).toBeGreaterThan(0);

  for (const reason of reasonList) {
    expect(typeof reason.code).toBe("string");
    expect(reason.code).toBeTruthy();
    expect(["satisfied", "missing", "partial", "blocked"]).toContain(reason.severity);
    expect(typeof reason.label).toBe("string");
    expect(reason.label).toBeTruthy();
    expect(typeof reason.detail).toBe("string");
    expect(reason.detail).toBeTruthy();
  }
}

test.describe("ACCESS2 Railway synthetic demo cases", () => {
  test("can log into the deployed ACCESS2 frontend", async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Patients" }).click();
    await expect(page.getByRole("heading", { name: "Patient queue" })).toBeVisible();
  });

  test("Demo Guide explains the seeded production demo path", async ({ page }) => {
    await login(page);

    await page.getByRole("link", { name: "Demo Guide" }).click();
    await expect(page).toHaveURL(/\/demo-guide$/);
    await expect(page.getByRole("heading", { name: "Demo Guide" })).toBeVisible();

    await expect(page.getByText(/signal -> escalation -> intervention -> outcome -> evidence/i)).toBeVisible();
    await expect(page.getByText(/immutable review packet snapshot -> approval\/rejection/i)).toBeVisible();
    await expect(page.getByText(/audit bundle -> manifest verification/i)).toBeVisible();

    const seededPatients = [
      "Demo Patient 1 - Audit Ready",
      "Demo Patient 2 - Missing Evidence",
      "Demo Patient 3 - Rejected Review",
      "Demo Patient 4 - Override Approval",
    ];
    for (const patientName of seededPatients) {
      await expect(page.getByRole("link", { name: patientName })).toBeVisible();
    }

    await expect(page.getByRole("heading", { name: "Evidence Chain" })).toBeVisible();
    await expect(
      page.getByText(/Summarizes whether the patient has the required signal-to-outcome proof chain/i),
    ).toBeVisible();

    await expect(page.getByRole("heading", { name: "Manifest Verification" })).toBeVisible();
    await expect(page.getByText(/Summarizes persisted review packet, audit bundle, and export posture/i)).toBeVisible();

    await expect(page.getByText("Synthetic/demo data only.")).toBeVisible();
    await expect(page.getByText("No real PHI.")).toBeVisible();
  });

  test("Demo Release Summary validates the production release posture", async ({ page }) => {
    await login(page);

    await page.getByRole("link", { name: "Release Summary" }).click();
    await expect(page).toHaveURL(/\/demo\/release-summary$/);
    await expect(page.getByRole("heading", { name: "Demo Release Summary" })).toBeVisible();

    const pageRoot = page.getByTestId("demo-release-summary-page");
    await expect(pageRoot).toContainText("https://access2.salvardata.com");
    await expect(pageRoot).toContainText("Demo Guide");
    await expect(pageRoot.getByRole("link", { name: "Available" })).toBeVisible();

    for (const scenarioText of [
      "Demo Patient 1 - Audit Ready",
      "Demo Patient 2 - Missing Evidence",
      "Demo Patient 3 - Rejected Review",
      "Demo Patient 4 - Override Approval",
      "Audit Ready",
      "Missing Evidence",
      "Rejected Review",
      "Override Approval",
    ]) {
      await expect(pageRoot).toContainText(scenarioText);
    }

    await expect(pageRoot).toContainText("Production E2E baseline");
    await expect(pageRoot).toContainText("8");
    await expect(pageRoot).toContainText("Passed");
    await expect(pageRoot).toContainText("2");
    await expect(pageRoot).toContainText("Skipped");
    await expect(pageRoot).toContainText("0");
    await expect(pageRoot).toContainText("Failed");

    const proofChecklist = pageRoot.locator("section", { hasText: "Evidence Proof Checklist" });
    await expect(proofChecklist).toBeVisible();
    await expect(proofChecklist).toContainText(
      "Read-only synthetic demo checklist for the ACCESS2 evidence story.",
    );

    for (const checklistText of [
      "Demo Patient 1 - Audit Ready",
      "Audit-ready because the signal-to-outcome proof chain is complete",
      "outcome: measurable improvement documented",
      "Demo Patient 2 - Missing Evidence",
      "Missing evidence because the patient has the care workflow context",
      "outcome: missing measurable outcome proof",
      "Demo Patient 3 - Rejected Review",
      "Rejected because the immutable review packet exists",
      "immutable review packet snapshot: rejected",
      "Demo Patient 4 - Override Approval",
      "Override-approved because the snapshot carries an approved override posture",
      "review posture: override-approved",
    ]) {
      await expect(proofChecklist).toContainText(checklistText);
    }

    for (const checklistLabel of [
      /signal/i,
      /escalation/i,
      /intervention/i,
      /outcome/i,
      /evidence/i,
      /case summary/i,
      /immutable review packet snapshot/i,
      /review posture/i,
      /audit bundle/i,
      /manifest verification/i,
      /readiness reasons/i,
      /next step/i,
    ]) {
      await expect(proofChecklist).toContainText(checklistLabel);
    }

    await expect(pageRoot).toContainText("No reviewer rejection mutation control is exposed in the V1 frontend.");
    await expect(pageRoot).toContainText(
      "No superuser override approval mutation control is exposed in the V1 frontend.",
    );
    await expect(
      pageRoot.getByRole("button", { name: /approve|reject|assign|override|export|create snapshot/i }),
    ).toHaveCount(0);
  });

  test("Reviewer Work Queue shows read-only review packet posture", async ({ page }) => {
    await login(page);

    await page.goto("/audit-readiness");
    await expect(page).toHaveURL(/\/audit-readiness$/);

    const pageRoot = page.getByTestId("audit-readiness-page");
    await expect(pageRoot).toContainText("ACCESS review packets");
    await expect(pageRoot).toContainText("Reviewer Work Queue");
    await expect(pageRoot).toContainText("Read-only V1 queue");
    await expect(pageRoot).toContainText("does not approve, reject, assign, export, or create snapshots");
    await expect(pageRoot).toContainText("Reviewer work queue");
    await expect(pageRoot).toContainText("Reviewer queue rows");

    for (const queueLabel of [
      "Audit ready",
      "Missing evidence / blocked",
      "Rejected review",
      "Override approval",
      "Exported bundle",
      "Pending / needs review",
    ]) {
      await expect(pageRoot).toContainText(queueLabel);
    }

    if (process.env.ACCESS2_E2E_DEMO_PATIENT_1_ID) {
      await expect(pageRoot.getByRole("link", { name: process.env.ACCESS2_E2E_DEMO_PATIENT_1_ID })).toBeVisible();
    }
    await expect(
      pageRoot.getByRole("button", { name: /approve|reject|assign|override|export|create snapshot/i }),
    ).toHaveCount(0);
    await expect(pageRoot.getByRole("link", { name: /Download JSON|Download Markdown|Download PDF/i })).toHaveCount(0);
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
    await expectOutcomeProofGapsPanel(page, [
      /Outcome proof gaps remain/i,
      /Signal\s*Satisfied/i,
      /Escalation\s*Satisfied/i,
      /Intervention\s*Satisfied/i,
      /Outcome\s*Missing/i,
      /Evidence\s*Missing/i,
      /Review Posture\s*Blocked/i,
      /Audit Bundle\s*Blocked/i,
      /Audit Bundle\s*Missing/i,
      /Snapshot is missing required evidence/i,
      /No measured outcome is documented/i,
      /Required evidence: Review packet is missing required evidence/i,
      /Audit bundle export is blocked until missing evidence is resolved/i,
      /No successful audit bundle export is recorded for this patient/i,
    ]);
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

    const persistedExportBundle = await exportAuditBundle(request, token, snapshotId);
    expectReadinessReasonShape(persistedExportBundle.readiness_reasons);
    expect(persistedExportBundle.readiness_reasons.map((reason) => reason.code)).toEqual(
      expect.arrayContaining(["audit_bundle_exported"]),
    );

    const verification = await verifyAuditManifest(request, token, snapshotId, bundle.audit_manifest);
    expect(verification.verified).toBe(true);
    expect(verification.mismatches).toEqual([]);

    await page.goto(`/patients/${patient.patient_id}`);
    await expectOutcomeProofGapsPanel(page, [
      /Outcome proof supports audit readiness/i,
      /Required proof elements are satisfied/i,
      /Signal\s*Satisfied/i,
      /Escalation\s*Satisfied/i,
      /Intervention\s*Satisfied/i,
      /Outcome\s*Satisfied/i,
      /Evidence\s*Satisfied/i,
      /Case Summary \/ Snapshot\s*Satisfied/i,
      /Review Posture\s*Satisfied/i,
      /Audit Bundle\s*Exported/i,
    ]);
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
    const backlogPanel = page.getByTestId("patient-review-packet-backlog-panel");
    await expect(backlogPanel.getByTestId("audit-bundle-download-actions")).toBeVisible();
    for (const label of ["Download JSON", "Download Markdown", "Download PDF"]) {
      const downloadLink = backlogPanel.getByRole("link", { name: label });
      await expect(downloadLink).toBeVisible();
      await expect(downloadLink).toHaveAttribute("href", new RegExp(`/audit-bundles/${snapshotId}/`));
    }

    const frontendBundle = await page.request.get(`/audit-bundles/${snapshotId}/json`);
    const frontendBundleText = await frontendBundle.text();
    expect(frontendBundle.ok(), frontendBundleText).toBeTruthy();
    expect(frontendBundle.headers()["content-type"]).toContain("application/json");
    const frontendBundlePayload = JSON.parse(frontendBundleText);
    expect(frontendBundlePayload.audit_manifest.snapshot_id).toBe(snapshotId);
    expectReadinessReasonShape(frontendBundlePayload.readiness_reasons);
    expect(frontendBundlePayload.readiness_reasons.map((reason: { code: string }) => reason.code)).toEqual(
      expect.arrayContaining(["audit_bundle_exported"]),
    );

    const markdownBundle = await page.request.get(`/audit-bundles/${snapshotId}/markdown`);
    const markdown = await markdownBundle.text();
    expect(markdownBundle.ok(), markdown).toBeTruthy();
    expect(markdownBundle.headers()["content-type"]).toContain("text/markdown");
    expect(markdown).toContain("Audit Readiness Reasons");
    expect(markdown).toContain("audit_bundle_exported");

    const pdfBundle = await page.request.get(`/audit-bundles/${snapshotId}/pdf`);
    const pdf = await pdfBundle.body();
    expect(pdfBundle.ok(), pdf.subarray(0, 200).toString("utf8")).toBeTruthy();
    expect(pdfBundle.headers()["content-type"]).toContain("application/pdf");
    expect(pdf.length).toBeGreaterThan(1000);
    expect(pdf.subarray(0, 4).toString("ascii")).toBe("%PDF");

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
    await expectOutcomeProofGapsPanel(page, [
      /Proof packet rejected/i,
      /Case Summary \/ Snapshot\s*Satisfied/i,
      /Review Posture\s*Blocked/i,
      /Latest review packet snapshot was rejected/i,
      /Audit Bundle\s*Blocked/i,
      /Audit Bundle\s*Missing/i,
      /Audit bundle export is blocked because the latest review packet was rejected/i,
      /No rejection controls are exposed here/i,
    ]);
    await expect(page.getByRole("button", { name: /reject/i })).toHaveCount(0);
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
    await expectOutcomeProofGapsPanel(page, [
      /Approval depends on override review/i,
      /override or superuser review/i,
      /Review Posture\s*Partial/i,
      /Override approval: Latest review packet snapshot was approved with override or superuser review/i,
      /Audit Bundle\s*Satisfied/i,
      /Override controls are not exposed in this read-only view/i,
    ]);
    await expect(page.getByRole("button", { name: /override/i })).toHaveCount(0);
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
