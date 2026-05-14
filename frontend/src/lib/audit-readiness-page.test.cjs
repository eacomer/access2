const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const pagePath = path.join(__dirname, "../app/audit-readiness/page.tsx");

function readPageSource() {
  return fs.readFileSync(pagePath, "utf8");
}

function extractImmutableSnapshotCopy(source) {
  const match = source.match(
    /data-testid="reviewer-immutable-snapshot-copy"[\s\S]*?<\/section>/,
  );
  assert.ok(match, "expected reviewer immutable snapshot copy section");
  return match[0];
}

test("audit readiness page renders key backend fields in the read-only worklist", () => {
  const source = readPageSource();

  [
    "Reviewer Work Queue",
    "Read-only V1 queue",
    "does not approve",
    "Reviewer queue rows",
    "Patient",
    "Queue Posture",
    "Latest Snapshot ID",
    "Snapshot Created",
    "Review Status",
    "Completion",
    "Review State",
    "Reviewer",
    "Next Step",
    "Bundle Available",
    "Exported",
    "Formats",
    "Audit ready",
    "Missing evidence / blocked",
    "Rejected review",
    "Override approval",
    "Needs review",
    "User ID:",
    "Unassigned",
  ].forEach((label) => {
    assert.match(source, new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  });

  [
    "formatAssignedReviewer",
    "item.patient_id",
    "item.latest_snapshot_id",
    "item.review_status",
    "item.review_state",
    "item.completion_status",
    "item.assigned_reviewer_user_id",
    "item.next_step.action",
    "item.next_step.reason",
    "item.audit_bundle.available",
    "item.audit_bundle.exported",
    "item.audit_bundle.export_formats",
    "fetchReviewPacketQueueSummary",
    "snapshot_audit_lifecycle",
    "approved_with_override_count",
    "exported_count",
  ].forEach((field) => {
    assert.match(source, new RegExp(field.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  });
});

test("audit readiness page explains immutable snapshot review posture", () => {
  const source = readPageSource();
  const immutableSnapshotCopy = extractImmutableSnapshotCopy(source);

  [
    "Reviewer Work Queue is read-only",
    "find and inspect persisted latest",
    "local gated V2",
    "production V1 remains read-only",
    "immutable audit record",
    "packet_json",
    "packet_markdown",
    "terminal historical evidence",
    "Only the latest pending_review snapshot can be actionable",
    "Historical snapshots",
    "stay read-only even after corrected evidence",
    "Corrections create a new review packet snapshot",
    "old rejected packet",
    "approval applies to the corrected latest pending",
    "audit bundle/manifest verification",
  ].forEach((label) => {
    assert.match(
      immutableSnapshotCopy,
      new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")),
    );
  });
});

test("audit readiness rows link to patient detail without exposing mutation controls", () => {
  const source = readPageSource();

  assert.match(source, /href=\{patientDetailHref\(item\.patient_id\)\}/);
  assert.match(source, /\/patients\/\$\{encodeURIComponent\(patientId\)\}/);
  assert.doesNotMatch(source, /method:\s*"POST"/);
  assert.doesNotMatch(source, /createWorkflowBootstrap/);
  assert.doesNotMatch(source, /acknowledgeEscalation/);
  assert.doesNotMatch(source, /Download JSON/);
  assert.doesNotMatch(source, /Download Markdown/);
  assert.doesNotMatch(source, /Download PDF/);
  assert.doesNotMatch(source, />\s*Approve\s*</i);
  assert.doesNotMatch(source, />\s*Reject\s*</i);
  assert.doesNotMatch(source, />\s*Assign\s*</i);
  assert.doesNotMatch(source, />\s*Override\s*</i);
  assert.doesNotMatch(source, />\s*Create Snapshot\s*</i);
  assert.doesNotMatch(source, /\/assignment/);
  assert.doesNotMatch(source, /assigned_reviewer_user_id:\s*/);
});

test("immutable snapshot copy stays read-only", () => {
  const source = readPageSource();
  const immutableSnapshotCopy = extractImmutableSnapshotCopy(source);

  assert.doesNotMatch(immutableSnapshotCopy, /<button/i);
  assert.doesNotMatch(immutableSnapshotCopy, /href=/i);
  assert.doesNotMatch(immutableSnapshotCopy, /method:\s*"POST"/);
  assert.doesNotMatch(immutableSnapshotCopy, /\/assignment/);
});
