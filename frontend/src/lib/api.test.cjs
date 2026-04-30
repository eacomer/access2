const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const apiPath = path.join(__dirname, "api.ts");

function loadApiModule() {
  const source = fs.readFileSync(apiPath, "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      esModuleInterop: true,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
    fileName: apiPath,
  });

  const apiModule = new Module(apiPath, module);
  apiModule.filename = apiPath;
  apiModule.paths = Module._nodeModulePaths(__dirname);
  apiModule.require = (request) => {
    if (request === "./auth/server-cookies") {
      return {
        getAuthTokenFromCookies: async () => "test-token",
      };
    }
    if (request === "./auth/session") {
      return {
        handleUnauthorized: () => {
          throw new Error("unauthorized");
        },
      };
    }
    return Module.prototype.require.call(apiModule, request);
  };
  apiModule._compile(outputText, apiPath);
  return apiModule.exports;
}

const api = loadApiModule();
const originalFetch = globalThis.fetch;
const originalBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
const originalConsoleLog = console.log;

function installJsonFetch(payload = {}) {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url: url.toString(), init });
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  return calls;
}

function assertJsonRequest(call) {
  assert.equal(call.init.headers.get("Accept"), "application/json");
  assert.equal(call.init.headers.get("Authorization"), "Bearer test-token");
  assert.equal(call.init.credentials, "include");
  assert.equal(call.init.cache, "no-store");
}

test.beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test/api/v1";
  console.log = () => {};
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
  process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
  console.log = originalConsoleLog;
});

test("fetchAuditReadiness sends status, limit, and offset query parameters", async () => {
  const calls = installJsonFetch({ items: [], total_count: 0, limit: 25, offset: 50, status_counts: {} });

  await api.fetchAuditReadiness({ status: "audit_ready", limit: 25, offset: 50 });

  assert.equal(calls.length, 1);
  const url = new URL(calls[0].url);
  assert.equal(url.pathname, "/api/v1/reports/access-review-packet/audit-readiness");
  assert.equal(url.searchParams.get("status"), "audit_ready");
  assert.equal(url.searchParams.get("limit"), "25");
  assert.equal(url.searchParams.get("offset"), "50");
  assertJsonRequest(calls[0]);
});

test("fetchAuditReadinessCsv sends optional status and returns Blob data", async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url: url.toString(), init });
    return new Response("patient_id\npatient-1\n", {
      status: 200,
      headers: { "Content-Type": "text/csv; charset=utf-8" },
    });
  };

  const blob = await api.fetchAuditReadinessCsv({ status: "review_ready" });

  assert.equal(calls.length, 1);
  const url = new URL(calls[0].url);
  assert.equal(url.pathname, "/api/v1/reports/access-review-packet/audit-readiness/export.csv");
  assert.equal(url.searchParams.get("status"), "review_ready");
  assert.equal(calls[0].init.headers.get("Accept"), "text/csv");
  assert.equal(blob instanceof Blob, true);
  assert.equal(await blob.text(), "patient_id\npatient-1\n");
});

test("fetchPatientAuditStatus uses the patient audit-status path", async () => {
  const calls = installJsonFetch({ patient_id: "patient-1" });

  await api.fetchPatientAuditStatus("patient-1");

  assert.equal(
    new URL(calls[0].url).pathname,
    "/api/v1/reports/access-review-packet/patients/patient-1/audit-status",
  );
});

test("fetchPatientBacklogDrillIn uses the patient backlog drill-in path", async () => {
  const calls = installJsonFetch({ patient_id: "patient-1", audit_status: {}, snapshots: [] });

  await api.fetchPatientBacklogDrillIn("patient-1", {
    reviewStatus: "pending_review",
    reviewReadinessStatus: "ready_for_review",
    limit: 10,
    offset: 20,
  });

  const url = new URL(calls[0].url);
  assert.equal(url.pathname, "/api/v1/reports/access-review-packet/snapshots/patient-backlog/patient-1");
  assert.equal(url.searchParams.get("review_status"), "pending_review");
  assert.equal(url.searchParams.get("review_readiness_status"), "ready_for_review");
  assert.equal(url.searchParams.get("limit"), "10");
  assert.equal(url.searchParams.get("offset"), "20");
});

test("fetchReviewerMySummary uses the reviewer summary endpoint and returns JSON", async () => {
  const payload = {
    assigned_to_me_count: 4,
    pending_assigned_ready_count: 2,
    blocked_missing_evidence_count: 1,
    oldest_pending_snapshot_created_at: "2026-04-01T12:00:00Z",
    pending_review_age: {
      new_today_count: 1,
      one_to_three_days_count: 1,
      four_to_seven_days_count: 1,
      over_seven_days_count: 1,
    },
  };
  const calls = installJsonFetch(payload);

  const result = await api.fetchReviewerMySummary();

  assert.equal(new URL(calls[0].url).pathname, "/api/v1/reports/access-review-packet/reviewer/my-summary");
  assert.deepEqual(result, payload);
  assertJsonRequest(calls[0]);
});

test("fetchReviewPacketQueueSummary uses the queue summary endpoint and returns JSON", async () => {
  const payload = {
    total: 7,
    review_status: {
      pending_review: 4,
      approved: 2,
      rejected: 1,
    },
    review_readiness_status: {
      ready_for_review: 3,
      missing_evidence: 1,
    },
    assigned: 5,
    unassigned: 2,
    pending_review_assigned: 3,
    pending_review_unassigned: 1,
    pending_review_ready_for_review: 3,
    pending_review_active_open_work: 1,
    pending_review_incomplete: 1,
    snapshot_audit_lifecycle: {
      pending_unassigned_count: 1,
      pending_assigned_ready_count: 3,
      blocked_missing_evidence_count: 1,
      approved_count: 2,
      approved_with_override_count: 1,
      rejected_count: 1,
      approved_not_exported_count: 1,
      exported_count: 1,
      pending_review_age: {
        new_today_count: 1,
        one_to_three_days_count: 1,
        four_to_seven_days_count: 1,
        over_seven_days_count: 1,
      },
    },
    audit_readiness_rollup: {
      incomplete_count: 1,
      review_ready_count: 3,
      approved_not_exported_count: 1,
      audit_ready_count: 1,
      rejected_count: 1,
    },
  };
  const calls = installJsonFetch(payload);

  const result = await api.fetchReviewPacketQueueSummary();

  assert.equal(
    new URL(calls[0].url).pathname,
    "/api/v1/reports/access-review-packet/snapshots/queue-summary",
  );
  assert.deepEqual(result, payload);
  assertJsonRequest(calls[0]);
});

test("fetchReviewerMySummary surfaces non-2xx responses", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "failure" }), {
      status: 503,
      statusText: "Service Unavailable",
      headers: { "Content-Type": "application/json" },
    });

  await assert.rejects(
    () => api.fetchReviewerMySummary(),
    /Request failed for \/api\/v1\/reports\/access-review-packet\/reviewer\/my-summary: 503 Service Unavailable/,
  );
});
