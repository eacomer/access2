const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const pagePath = path.join(__dirname, "../app/demo/release-summary/page.tsx");
const navPath = path.join(__dirname, "../components/AppNavigation.tsx");

function readSource(filePath) {
  return fs.readFileSync(filePath, "utf8");
}

test("demo release summary page renders the protected V1 release posture", () => {
  const source = readSource(pagePath);

  [
    "demo-release-summary-page",
    "Demo Release Summary",
    "https://access2.salvardata.com",
    "NEXT_PUBLIC_API_BASE_URL",
    "Available",
    "Demo Patient 1 - Audit Ready",
    "Demo Patient 2 - Missing Evidence",
    "Demo Patient 3 - Rejected Review",
    "Demo Patient 4 - Override Approval",
    "Audit Ready",
    "Missing Evidence",
    "Rejected Review",
    "Override Approval",
    "6",
    "2",
    "0",
    "No reviewer rejection mutation control is exposed in the V1 frontend.",
    "No superuser override approval mutation control is exposed in the V1 frontend.",
  ].forEach((text) => {
    assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  });

  assert.match(source, /requireAuth\("\/demo\/release-summary"\)/);
});

test("demo release summary remains read-only and linked from primary navigation", () => {
  const pageSource = readSource(pagePath);
  const navSource = readSource(navPath);

  assert.match(navSource, /href:\s*"\/demo\/release-summary"/);
  assert.match(navSource, /label:\s*"Release Summary"/);
  assert.doesNotMatch(pageSource, />\s*Approve\s*</i);
  assert.doesNotMatch(pageSource, />\s*Reject\s*</i);
  assert.doesNotMatch(pageSource, /method:\s*"POST"/i);
  assert.doesNotMatch(pageSource, /fetch\(/i);
});
