const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const routePath = path.join(
  __dirname,
  "../app/audit-bundles/[snapshotId]/[format]/route.ts",
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

  static redirect(url) {
    return new TestNextResponse(null, {
      status: 307,
      headers: {
        Location: url.toString(),
      },
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
    if (request === "../../../../lib/auth/session") {
      return {
        buildLoginRedirectUrl: (rawNext) => `/login?next=${encodeURIComponent(rawNext || "/patients")}`,
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

function buildRequest(format, snapshotId = "snapshot-1") {
  const url = `http://frontend.test/audit-bundles/${encodeURIComponent(snapshotId)}/${format}`;
  return {
    nextUrl: new URL(url),
    url,
  };
}

function buildContext(format, snapshotId = "snapshot-1") {
  return {
    params: Promise.resolve({
      snapshotId,
      format,
    }),
  };
}

async function callRoute(format, snapshotId = "snapshot-1") {
  return route.GET(buildRequest(format, snapshotId), buildContext(format, snapshotId));
}

test.beforeEach(() => {
  authToken = "test-token";
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test/api/v1";
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
  process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
});

test("audit bundle route maps supported formats to fixed backend endpoints", async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url: url.toString(), init });
    return new Response("bundle", {
      status: 200,
      headers: {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": "attachment; filename=from-backend.dat",
      },
    });
  };

  const cases = [
    {
      format: "json",
      accept: "application/json",
      pathname: "/api/v1/reports/access-review-packet/snapshots/snapshot-1/audit-bundle",
    },
    {
      format: "markdown",
      accept: "text/markdown",
      pathname: "/api/v1/reports/access-review-packet/snapshots/snapshot-1/audit-bundle/markdown",
    },
    {
      format: "pdf",
      accept: "application/pdf",
      pathname: "/api/v1/reports/access-review-packet/snapshots/snapshot-1/audit-bundle/pdf",
    },
  ];

  for (const entry of cases) {
    const response = await callRoute(entry.format);

    assert.equal(response.status, 200);
    assert.equal(await response.text(), "bundle");
    assert.equal(response.headers.get("Content-Type"), "application/octet-stream");
    assert.equal(response.headers.get("Content-Disposition"), "attachment; filename=from-backend.dat");
  }

  assert.equal(calls.length, cases.length);
  cases.forEach((entry, index) => {
    const call = calls[index];
    const url = new URL(call.url);
    assert.equal(url.pathname, entry.pathname);
    assert.equal(call.init.headers.Accept, entry.accept);
    assert.equal(call.init.headers.Authorization, "Bearer test-token");
    assert.equal(call.init.cache, "no-store");
  });
});

test("audit bundle route rejects unsupported formats without calling the backend", async () => {
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called for unsupported formats");
  };

  const response = await callRoute("zip");

  assert.equal(response.status, 404);
  assert.deepEqual(await response.json(), { error: "Unsupported audit bundle format." });
});

test("audit bundle route redirects to login when no auth token is available", async () => {
  authToken = null;
  globalThis.fetch = async () => {
    throw new Error("fetch should not be called without auth");
  };

  const response = await callRoute("json");

  assert.equal(response.status, 307);
  assert.equal(
    response.headers.get("Location"),
    "http://frontend.test/login?next=%2Faudit-bundles%2Fsnapshot-1%2Fjson",
  );
});

test("audit bundle route redirects to login when the backend reports expired auth", async () => {
  globalThis.fetch = async () => new Response("expired", { status: 401 });

  const response = await callRoute("json");

  assert.equal(response.status, 307);
  assert.equal(
    response.headers.get("Location"),
    "http://frontend.test/login?next=%2Faudit-bundles%2Fsnapshot-1%2Fjson",
  );
});

test("audit bundle route surfaces backend non-2xx responses safely", async () => {
  globalThis.fetch = async () =>
    new Response("Snapshot is not approved.", {
      status: 409,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
      },
    });

  const response = await callRoute("pdf");

  assert.equal(response.status, 409);
  assert.equal(response.headers.get("Content-Type"), "text/plain; charset=utf-8");
  assert.equal(await response.text(), "Snapshot is not approved.");
});

test("audit bundle route encodes snapshot ids and provides fallback download headers", async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url: url.toString(), init });
    return new Response(new Uint8Array([1, 2, 3]), {
      status: 200,
    });
  };

  const response = await callRoute("pdf", "snapshot 1/with slash");

  assert.equal(calls.length, 1);
  assert.equal(
    new URL(calls[0].url).pathname,
    "/api/v1/reports/access-review-packet/snapshots/snapshot%201%2Fwith%20slash/audit-bundle/pdf",
  );
  assert.equal(response.headers.get("Content-Type"), "application/pdf");
  assert.equal(
    response.headers.get("Content-Disposition"),
    'attachment; filename="access2-audit-bundle-snapshot-1-with-slash.pdf"',
  );
});
