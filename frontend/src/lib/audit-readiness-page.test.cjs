const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const pagePath = path.join(__dirname, "../app/audit-readiness/page.tsx");

function readPageSource() {
  return fs.readFileSync(pagePath, "utf8");
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
