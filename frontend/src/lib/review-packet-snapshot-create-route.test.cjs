const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const routePath = path.join(
  __dirname,
  "../app/review-packet-snapshots/patients/[patientId]/create/route.ts",
);

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
    if (request === "../../../../../lib/auth/server-cookies") {
      return {
        getAuthTokenFromCookies: async () => authToken,
      };
    }
    if (request === "../../../../../lib/api") {
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

function buildContext(patientId = "patient-1") {
  return {
    params: Promise.resolve({ patientId }),
  };
}

async function callRoute(patientId = "patient-1") {
  return route.POST({}, buildContext(patientId));
}

test.beforeEach(() => {
  authToken = "test-token";
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test/api/v1";
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
  process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
});

test("review packet snapshot create route forwards to backend create-snapshot endpoint", async () => {
  const calls = [];
  const payload = {
    id: "snapshot-new",
    patient_id: "patient-1",
    review_status: "pending_review",
    packet_json: { patient_id: "patient-1" },
    packet_markdown: "# ACCESS Review Packet",
  };
  globalThis.fetch = async (url, init) => {
    calls.push({ url: url.toString(), init });
    return new Response(JSON.stringify(payload), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
  };

  const response = await callRoute("patient-1");

  assert.equal(response.status, 201);
  assert.deepEqual(await response.json(), payload);
  assert.equal(calls.length, 1);
  const call = calls[0];
  assert.equal(
    new URL(call.url).pathname,
    "/api/v1/reports/access-review-packet/patient-1/snapshots",
  );
  assert.equal(call.init.method, "POST");
  assert.equal(call.init.headers.Accept, "application/json");
  assert.equal(call.init.headers.Authorization, "Bearer test-token");
  assert.equal(call.init.cache, "no-store");
  assert.equal("body" in call.init, false);
});

test("review packet snapshot create route preserves backend errors", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Patient not found." }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });

  const response = await callRoute("missing-patient");

  assert.equal(response.status, 404);
  assert.deepEqual(await response.json(), { error: "Patient not found." });
});

test("review packet snapshot create route requires auth before calling backend", async () => {
  authToken = null;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called without auth");
  };

  const response = await callRoute("patient-1");

  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), {
    error: "Sign in is required to create a review packet snapshot.",
  });
});
