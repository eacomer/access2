const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const pagePath = path.join(__dirname, "../app/patients/[id]/page.tsx");

function readPageSource() {
  return fs.readFileSync(pagePath, "utf8");
}

function extractOutcomeProofGapsRenderer(source) {
  const start = source.indexOf("const renderOutcomeProofGapsPanel");
  const end = source.indexOf("const renderEvidenceChainPanel");
  assert.notEqual(start, -1);
  assert.notEqual(end, -1);
  return source.slice(start, end);
}

function extractAuditBundleUnavailableHelper(source) {
  const start = source.indexOf("const getAuditBundleUnavailableMessage");
  const end = source.indexOf("const getAuditBundleDownloadHref");
  assert.notEqual(start, -1);
  assert.notEqual(end, -1);
  return source.slice(start, end);
}

function extractPatientBacklogRenderer(source) {
  const start = source.indexOf("const renderPatientBacklogPanel");
  const end = source.indexOf("export default async function PatientDetailPage");
  assert.notEqual(start, -1);
  assert.notEqual(end, -1);
  return source.slice(start, end);
}

function extractCorrectionLoopStatusMessaging(source) {
  const start = source.indexOf('data-testid="patient-correction-loop-status"');
  const end = source.indexOf('<div className="queue-impact-grid">', start);
  assert.notEqual(start, -1);
  assert.notEqual(end, -1);
  return source.slice(start, end);
}

test("patient detail renders outcome proof gaps as a read-only audit section", () => {
  const source = readPageSource();
  const renderer = extractOutcomeProofGapsRenderer(source);

  assert.match(source, /data-testid="patient-outcome-proof-gaps-panel"/);
  assert.match(source, /Outcome Proof Gaps/);
  assert.match(source, /renderOutcomeProofGapsPanel\(\{/);
  assert.match(source, /readiness_reasons/);
  assert.match(source, /READINESS_REASON_PROOF_ELEMENT_LABELS/);
  assert.match(source, /signal_present/);
  assert.match(source, /review_rejected/);
  assert.match(source, /review_override_approved/);
  assert.match(source, /audit_bundle_blocked_missing_evidence/);
  assert.match(renderer, /backendReadinessReasons\.length > 0/);
  assert.match(renderer, /fallbackRows/);

  [
    "Signal",
    "Escalation",
    "Intervention",
    "Outcome",
    "Evidence",
    "Case Summary / Snapshot",
    "Review Posture",
    "Audit Bundle",
  ].forEach((label) => {
    assert.match(renderer, new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  });

  assert.doesNotMatch(renderer, /<button/i);
  assert.doesNotMatch(renderer, /<a\s/i);
  assert.doesNotMatch(renderer, /href=/i);
  assert.doesNotMatch(renderer, /method:\s*"POST"/i);
});

test("outcome proof gaps cover ready, missing evidence, rejected, and override postures", () => {
  const renderer = extractOutcomeProofGapsRenderer(readPageSource());

  [
    "Outcome proof supports audit readiness",
    "Outcome proof gaps remain",
    "Proof packet rejected",
    "Approval depends on override review",
    "No rejection controls are exposed here.",
    "Override controls are not exposed in this read-only view.",
  ].forEach((text) => {
    assert.match(renderer, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  });
});

test("patient detail exposes audit bundle downloads only for approved export-ready snapshots", () => {
  const source = readPageSource();
  const helper = extractAuditBundleUnavailableHelper(source);
  const renderer = extractPatientBacklogRenderer(source);

  assert.match(source, /const AUDIT_BUNDLE_DOWNLOADS = \[/);
  assert.match(source, /format: "json", label: "Download JSON"/);
  assert.match(source, /format: "markdown", label: "Download Markdown"/);
  assert.match(source, /format: "pdf", label: "Download PDF"/);

  assert.match(helper, /snapshot\.review_status === "rejected"/);
  assert.match(helper, /Unavailable for rejected snapshots/);
  assert.match(helper, /snapshot\.review_status !== "approved"/);
  assert.match(helper, /Unavailable until the snapshot is approved and export-ready/);
  assert.match(helper, /!backlog\.audit_status\.audit_bundle\.available/);
  assert.match(helper, /Approved snapshot is not export-ready/);

  assert.match(renderer, /data-testid="audit-bundle-download-actions"/);
  assert.match(renderer, /getAuditBundleDownloadHref/);
  assert.match(renderer, /Available only for approved snapshots through the persisted audit bundle/);
  assert.match(renderer, /audit_bundle_exported events/);
  assert.doesNotMatch(renderer, /method:\s*"POST"/i);
  assert.doesNotMatch(renderer, /override_missing_checklist/);
});

test("patient detail renders assigned reviewer metadata and gates assignment to the backlog", () => {
  const source = readPageSource();
  const renderer = extractPatientBacklogRenderer(source);

  assert.match(source, /const formatAssignedReviewer/);
  assert.match(source, /Assigned reviewer/);
  assert.match(source, /auditStatus\.assigned_reviewer_user_id/);
  assert.match(renderer, /snapshot\.assigned_reviewer_user_id/);
  assert.match(source, /User ID: \$\{assignedReviewerUserId\}/);
  assert.match(source, /Unassigned/);
  assert.match(source, /ReviewerAssignmentControl/);
  assert.match(renderer, /<ReviewerAssignmentControl/);
  assert.match(renderer, /latestSnapshotId=\{latestSnapshotId\}/);
  assert.match(renderer, /reviewStatus=\{snapshot\.review_status\}/);
  assert.match(renderer, /snapshotId=\{snapshot\.id\}/);
});

test("patient detail explains correction-loop snapshot posture as read-only status messaging", () => {
  const source = readPageSource();
  const renderer = extractPatientBacklogRenderer(source);
  const messaging = extractCorrectionLoopStatusMessaging(source);

  [
    "Correction loop status",
    "Latest actionable packet",
    "only the latest pending_review snapshot can expose assignment, rejection, or",
    "approval controls",
    "Historical packets",
    "rejected and approved snapshots are audit evidence",
    "packet_json",
    "packet_markdown",
    "terminal snapshots stay read-only",
    "Corrected snapshots",
    "corrections create a new review packet snapshot from current evidence",
    "new latest pending_review snapshot before approval",
    "approval applies to that corrected",
    "not the old rejected packet",
    "Read-only posture",
    "approved/rejected snapshots expose no mutation controls",
    "Reviewer Work Queue remains",
    "production V1 remains read-only",
    "V2 mutation behavior is local-only and gated",
  ].forEach((text) => {
    assert.match(renderer, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  });

  assert.doesNotMatch(messaging, /<button/i);
  assert.doesNotMatch(messaging, /<a\s/i);
  assert.doesNotMatch(messaging, /href=/i);
  assert.doesNotMatch(messaging, /method:\s*"POST"/i);
});
