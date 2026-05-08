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
