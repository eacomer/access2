const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const routePath = path.join(
  __dirname,
  "../app/review-packet-snapshots/[snapshotId]/assignment/route.ts",
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
    if (request === "../../../../lib/auth/server-cookies") {
      return {
        getAuthTokenFromCookies: async () => authToken,
      };
    }
    if (request === "../../../../lib/api") {
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

function buildContext(snapshotId = "snapshot-1") {
  return {
    params: Promise.resolve({ snapshotId }),
  };
}

async function callRoute(body, snapshotId = "snapshot-1") {
  return route.POST(buildRequest(body), buildContext(snapshotId));
}

test.beforeEach(() => {
  authToken = "test-token";
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test/api/v1";
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
  process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
});

test("reviewer assignment route validates missing and blank reviewer IDs without calling backend", async () => {
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called for invalid local requests");
  };

  const missing = await callRoute({});
  assert.equal(missing.status, 400);
  assert.deepEqual(await missing.json(), { error: "Reviewer user ID required." });

  const blank = await callRoute({ assignedReviewerUserId: "   " });
  assert.equal(blank.status, 400);
  assert.deepEqual(await blank.json(), { error: "Reviewer user ID required." });
});

test("reviewer assignment route forwards valid assignment payload", async () => {
  const calls = [];
  const payload = {
    id: "snapshot-1",
    review_status: "pending_review",
    assigned_reviewer_user_id: "reviewer-1",
  };
  globalThis.fetch = async (url, init) => {
    calls.push({ url: url.toString(), init });
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const response = await callRoute({ assigned_reviewer_user_id: "  reviewer-1  " });

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), payload);
  assert.equal(calls.length, 1);
  const call = calls[0];
  assert.equal(
    new URL(call.url).pathname,
    "/api/v1/reports/access-review-packet/snapshots/snapshot-1/assignment",
  );
  assert.equal(call.init.method, "PATCH");
  assert.equal(call.init.headers.Accept, "application/json");
  assert.equal(call.init.headers.Authorization, "Bearer test-token");
  assert.equal(call.init.headers["Content-Type"], "application/json");
  assert.equal(call.init.cache, "no-store");
  assert.deepEqual(JSON.parse(call.init.body), {
    assigned_reviewer_user_id: "reviewer-1",
  });
});

test("reviewer assignment route rejects successful backend responses that did not persist assignment", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        id: "snapshot-1",
        review_status: "pending_review",
        assigned_reviewer_user_id: null,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );

  const response = await callRoute({ assigned_reviewer_user_id: "reviewer-1" });

  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), {
    error: "Review packet snapshot assignment did not persist.",
  });
});

test("reviewer assignment route preserves backend 422 and 409 errors", async () => {
  const cases = [
    { status: 422, detail: "Invalid assigned_reviewer_user_id." },
    { status: 409, detail: "Terminal review states cannot be reassigned." },
  ];

  for (const entry of cases) {
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ detail: entry.detail }), {
        status: entry.status,
        headers: { "Content-Type": "application/json" },
      });

    const response = await callRoute({ assignedReviewerUserId: "reviewer-1" });

    assert.equal(response.status, entry.status);
    assert.deepEqual(await response.json(), { error: entry.detail });
  }
});

test("reviewer assignment route requires auth before calling backend", async () => {
  authToken = null;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called without auth");
  };

  const response = await callRoute({ assignedReviewerUserId: "reviewer-1" });

  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), {
    error: "Sign in is required to assign a review packet snapshot.",
  });
});
