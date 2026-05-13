const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const routePath = path.join(
  __dirname,
  "../app/review-packet-snapshots/[snapshotId]/approve/route.ts",
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

function buildContext(snapshotId = "snapshot-1") {
  return {
    params: Promise.resolve({ snapshotId }),
  };
}

async function callRoute(snapshotId = "snapshot-1") {
  return route.POST({}, buildContext(snapshotId));
}

test.beforeEach(() => {
  authToken = "test-token";
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test/api/v1";
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
  process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
});

test("review packet approval route forwards approved review payload", async () => {
  const calls = [];
  const payload = {
    id: "snapshot-1",
    review_status: "approved",
  };
  globalThis.fetch = async (url, init) => {
    calls.push({ url: url.toString(), init });
    return new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  const response = await callRoute();

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), payload);
  assert.equal(calls.length, 1);
  const call = calls[0];
  assert.equal(
    new URL(call.url).pathname,
    "/api/v1/reports/access-review-packet/snapshots/snapshot-1/review",
  );
  assert.equal(call.init.method, "PATCH");
  assert.equal(call.init.headers.Accept, "application/json");
  assert.equal(call.init.headers.Authorization, "Bearer test-token");
  assert.equal(call.init.headers["Content-Type"], "application/json");
  assert.equal(call.init.cache, "no-store");
  assert.deepEqual(JSON.parse(call.init.body), {
    review_status: "approved",
  });
});

test("review packet approval route preserves backend approval errors", async () => {
  const cases = [
    { status: 409, detail: "Snapshot cannot be approved while persisted review_checklist has missing items." },
    { status: 409, detail: "Terminal review states cannot be rewritten." },
  ];

  for (const entry of cases) {
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ detail: entry.detail }), {
        status: entry.status,
        headers: { "Content-Type": "application/json" },
      });

    const response = await callRoute();

    assert.equal(response.status, entry.status);
    assert.deepEqual(await response.json(), { error: entry.detail });
  }
});

test("review packet approval route fails closed when backend does not persist approval", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ id: "snapshot-1", review_status: "pending_review" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

  const response = await callRoute();

  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), {
    error: "Review packet snapshot approval did not persist.",
  });
});

test("review packet approval route requires auth before calling backend", async () => {
  authToken = null;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called without auth");
  };

  const response = await callRoute();

  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), {
    error: "Sign in is required to approve a review packet snapshot.",
  });
});
