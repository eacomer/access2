const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const pagePath = path.join(__dirname, "../app/demo-guide/page.tsx");

function readSource(filePath) {
  return fs.readFileSync(filePath, "utf8");
}

test("demo guide explains stakeholder proof posture and current baseline", () => {
  const source = readSource(pagePath);

  [
    "demo-guide-page",
    "Demo Guide",
    "care update",
    "resolution",
    "ACCESS2 is not just a worklist",
    "approved review packets and audit bundles can defend reimbursement evidence",
    "8 passed, 2 skipped, 0 failed",
    "read-only seeded demo postures",
    "V2 correction-loop mutation stays localhost-only",
    "fail-closed host guards",
  ].forEach((text) => {
    assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  });

  assert.match(source, /disposable synthetic\s+data/);
  assert.match(source, /requireAuth\("\/demo-guide"\)/);
});

test("demo guide remains read-only guidance", () => {
  const source = readSource(pagePath);

  assert.doesNotMatch(source, />\s*Approve\s*</i);
  assert.doesNotMatch(source, />\s*Reject\s*</i);
  assert.doesNotMatch(source, /method:\s*"POST"/i);
  assert.doesNotMatch(source, /fetch\(/i);
});
