const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const pagePath = path.join(__dirname, "../app/audit-bundle-verify/page.tsx");
const formPath = path.join(__dirname, "../app/audit-bundle-verify/AuditBundleVerifyForm.tsx");

function readSource(filePath) {
  return fs.readFileSync(filePath, "utf8");
}

test("audit bundle verify page renders an authenticated verification support screen", () => {
  const pageSource = readSource(pagePath);
  const formSource = readSource(formPath);
  const combined = `${pageSource}\n${formSource}`;

  [
    "audit-bundle-verify-page",
    "audit-bundle-verify-form",
    "Snapshot ID",
    "Audit manifest JSON",
    "Verify Manifest",
    "Verified",
    "Mismatch",
    "Invalid manifest",
    "Request error",
  ].forEach((text) => {
    assert.match(combined, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  });

  assert.match(pageSource, /requireAuth\("\/audit-bundle-verify"\)/);
});

test("audit bundle verify form posts to the frontend verification proxy", () => {
  const formSource = readSource(formPath);

  assert.match(formSource, /fetch\("\/audit-bundle-verify\/verify"/);
  assert.match(formSource, /method:\s*"POST"/);
  assert.match(formSource, /auditManifest/);
  assert.match(formSource, /JSON\.parse\(manifestText\)/);
});

test("audit bundle verify page does not expose workflow mutation controls", () => {
  const combined = `${readSource(pagePath)}\n${readSource(formPath)}`;

  assert.doesNotMatch(combined, />\s*Approve\s*</i);
  assert.doesNotMatch(combined, />\s*Reject\s*</i);
  assert.doesNotMatch(combined, />\s*Assign\s*</i);
  assert.doesNotMatch(combined, />\s*Export\s*</i);
  assert.doesNotMatch(combined, />\s*Edit\s*</i);
  assert.doesNotMatch(combined, /createWorkflowBootstrap|createInterventionTask|updateEscalationStatus/);
});
