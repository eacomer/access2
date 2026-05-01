const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const routePath = path.join(__dirname, "../app/audit-bundle-verify/verify/route.ts");

let authToken = "test-token";

class TestNextResponse extends Response {
  static json(body, init = {}) {
    const headers = new Headers(init.headers);
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    return new TestNextResponse(JSON.stringify(body), {
      ...init,
      headers,
    });
  }
}

function loadRouteModule() {
  const source = fs.readFileSync(routePath, "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      esModuleInterop: true,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
    fileName: routePath,
  });

  const routeModule = new Module(routePath, module);
  routeModule.filename = routePath;
  routeModule.paths = Module._nodeModulePaths(path.dirname(routePath));
  routeModule.require = (request) => {
    if (request === "next/server") {
      return {
        NextRequest: class {},
        NextResponse: TestNextResponse,
      };
    }
    if (request === "../../../lib/auth/server-cookies") {
      return {
        getAuthTokenFromCookies: async () => authToken,
      };
    }
    if (request === "../../../lib/api") {
      return {
        getApiBaseUrl: () => process.env.NEXT_PUBLIC_API_BASE_URL || "http://api.test/api/v1",
      };
    }
    return Module.prototype.require.call(routeModule, request);
  };
  routeModule._compile(outputText, routePath);
  return routeModule.exports;
}

const route = loadRouteModule();
const originalFetch = globalThis.fetch;
const originalBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

function buildRequest(body) {
  return {
    json: async () => body,
  };
}

async function callRoute(body) {
  return route.POST(buildRequest(body));
}

const manifest = {
  snapshot_id: "snapshot-1",
  patient_id: "patient-1",
  review_status: "approved",
  generated_from: "persisted_snapshot",
  packet_json_sha256: "json-hash",
  packet_markdown_sha256: "markdown-hash",
  decision_event_count: 1,
  approval_event_id: "approval-1",
  approval_override_used: false,
};

test.beforeEach(() => {
  authToken = "test-token";
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test/api/v1";
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
  process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
});

test("audit bundle verify route posts manifest to the expected backend endpoint", async () => {
  const calls = [];
  const payload = {
    snapshot_id: "snapshot-1",
    verified: true,
    mismatches: [],
    expected_manifest: manifest,
  };
  globalThis.fetch = async (url, init) => {
    calls.push({ url: url.toString(), init });
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const response = await callRoute({
    snapshotId: "snapshot-1",
    auditManifest: manifest,
  });

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), payload);
  assert.equal(calls.length, 1);
  const call = calls[0];
  assert.equal(
    new URL(call.url).pathname,
    "/api/v1/reports/access-review-packet/snapshots/snapshot-1/audit-bundle/verify",
  );
  assert.equal(call.init.method, "POST");
  assert.equal(call.init.headers.Accept, "application/json");
  assert.equal(call.init.headers.Authorization, "Bearer test-token");
  assert.equal(call.init.headers["Content-Type"], "application/json");
  assert.equal(call.init.cache, "no-store");
  assert.deepEqual(JSON.parse(call.init.body), { audit_manifest: manifest });
});

test("audit bundle verify route returns mismatch payloads from the backend", async () => {
  const payload = {
    snapshot_id: "snapshot-1",
    verified: false,
    mismatches: [
      {
        field: "packet_json_sha256",
        expected: "expected-hash",
        actual: "submitted-hash",
      },
    ],
    expected_manifest: {
      ...manifest,
      packet_json_sha256: "expected-hash",
    },
  };
  globalThis.fetch = async () =>
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

  const response = await callRoute({
    snapshotId: "snapshot-1",
    auditManifest: manifest,
  });

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), payload);
});

test("audit bundle verify route validates local request shape without calling the backend", async () => {
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called for invalid local requests");
  };

  const missingSnapshot = await callRoute({ snapshotId: "", auditManifest: manifest });
  assert.equal(missingSnapshot.status, 400);
  assert.deepEqual(await missingSnapshot.json(), { error: "Snapshot ID is required." });

  const missingManifest = await callRoute({ snapshotId: "snapshot-1", auditManifest: null });
  assert.equal(missingManifest.status, 400);
  assert.deepEqual(await missingManifest.json(), { error: "auditManifest must be a JSON object." });
});

test("audit bundle verify route returns backend errors without stack traces", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Snapshot not found." }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });

  const response = await callRoute({
    snapshotId: "snapshot-1",
    auditManifest: manifest,
  });

  assert.equal(response.status, 404);
  assert.deepEqual(await response.json(), { error: "Snapshot not found." });
});

test("audit bundle verify route requires auth before calling the backend", async () => {
  authToken = null;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called without auth");
  };

  const response = await callRoute({
    snapshotId: "snapshot-1",
    auditManifest: manifest,
  });

  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), {
    error: "Sign in is required to verify an audit bundle.",
  });
});
