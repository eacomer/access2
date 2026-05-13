const assert = require("node:assert/strict");
const fs = require("node:fs");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");
const ts = require("typescript");

const guardPath = path.join(__dirname, "../../e2e/helpers/mutation-host-guard.ts");

function loadGuardModule() {
  const source = fs.readFileSync(guardPath, "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      esModuleInterop: true,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
    fileName: guardPath,
  });

  const guardModule = new Module(guardPath, module);
  guardModule.filename = guardPath;
  guardModule.paths = Module._nodeModulePaths(path.dirname(guardPath));
  guardModule._compile(outputText, guardPath);
  return guardModule.exports;
}

const { assertSafeMutationE2ETargets, sanitizeMutationTargetForError } = loadGuardModule();

function assertBlocked(targets, expectedMessage) {
  assert.throws(
    () => assertSafeMutationE2ETargets(targets),
    (error) => {
      assert.match(error.message, /Mutation E2E is blocked/);
      assert.match(error.message, expectedMessage);
      return true;
    },
  );
}

test("mutation host guard allows localhost frontend and backend targets", () => {
  assert.doesNotThrow(() =>
    assertSafeMutationE2ETargets([
      { label: "ACCESS2_E2E_BASE_URL", url: "http://localhost:3001" },
      { label: "ACCESS2_E2E_API_BASE_URL", url: "http://localhost:8000/api/v1" },
    ]),
  );
});

test("mutation host guard allows 127.0.0.1 frontend and backend targets", () => {
  assert.doesNotThrow(() =>
    assertSafeMutationE2ETargets([
      { label: "ACCESS2_E2E_BASE_URL", url: "http://127.0.0.1:3001" },
      { label: "ACCESS2_E2E_API_BASE_URL", url: "http://127.0.0.1:8000/api/v1" },
    ]),
  );
});

test("mutation host guard allows IPv6 loopback targets", () => {
  assert.doesNotThrow(() =>
    assertSafeMutationE2ETargets([
      { label: "ACCESS2_E2E_BASE_URL", url: "http://[::1]:3001" },
      { label: "ACCESS2_E2E_API_BASE_URL", url: "http://[::1]:8000/api/v1" },
    ]),
  );
});

test("mutation host guard blocks the production frontend custom domain", () => {
  assertBlocked(
    [{ label: "ACCESS2_E2E_BASE_URL", url: "https://access2.salvardata.com" }],
    /production-like host access2\.salvardata\.com/,
  );
});

test("mutation host guard blocks the production API custom domain", () => {
  assertBlocked(
    [{ label: "ACCESS2_E2E_API_BASE_URL", url: "https://api.salvardata.com/api/v1" }],
    /production-like host api\.salvardata\.com/,
  );
});

test("mutation host guard blocks railway.app hosts", () => {
  assertBlocked(
    [{ label: "ACCESS2_E2E_BASE_URL", url: "https://access2-production.railway.app" }],
    /production-like host access2-production\.railway\.app/,
  );
});

test("mutation host guard blocks up.railway.app hosts", () => {
  assertBlocked(
    [{ label: "ACCESS2_E2E_BASE_URL", url: "https://access2-production.up.railway.app" }],
    /production-like host access2-production\.up\.railway\.app/,
  );
});

test("mutation host guard blocks hosts containing production markers", () => {
  assertBlocked(
    [{ label: "ACCESS2_E2E_API_BASE_URL", url: "https://api.salvardata.com.evil.test/api/v1" }],
    /production-like host api\.salvardata\.com\.evil\.test/,
  );
});

test("mutation host guard blocks production URL values without exposing credentials or query strings", () => {
  assert.throws(
    () =>
      assertSafeMutationE2ETargets([
        {
          label: "ACCESS2_E2E_BASE_URL",
          url: "https://user:password@access2.salvardata.com/path?token=secret",
        },
      ]),
    (error) => {
      assert.match(error.message, /Mutation E2E is blocked/);
      assert.match(error.message, /production-like host access2\.salvardata\.com/);
      assert.doesNotMatch(error.message, /password|token|secret|user|path/);
      return true;
    },
  );
});

test("mutation host guard blocks mixed pairs with localhost frontend and production API", () => {
  assertBlocked(
    [
      { label: "ACCESS2_E2E_BASE_URL", url: "http://localhost:3001" },
      { label: "ACCESS2_E2E_API_BASE_URL", url: "https://api.salvardata.com/api/v1" },
    ],
    /production-like host api\.salvardata\.com/,
  );
});

test("mutation host guard blocks mixed pairs with production frontend and localhost API", () => {
  assertBlocked(
    [
      { label: "ACCESS2_E2E_BASE_URL", url: "https://access2.salvardata.com" },
      { label: "ACCESS2_E2E_API_BASE_URL", url: "http://localhost:8000/api/v1" },
    ],
    /production-like host access2\.salvardata\.com/,
  );
});

test("mutation host guard blocks undefined URL values", () => {
  assertBlocked([{ label: "ACCESS2_E2E_BASE_URL", url: undefined }], /missing URL/);
});

test("mutation host guard blocks missing URL values", () => {
  assertBlocked([{ label: "ACCESS2_E2E_BASE_URL", url: "" }], /missing URL/);
});

test("mutation host guard blocks malformed URL values", () => {
  assertBlocked([{ label: "ACCESS2_E2E_BASE_URL", url: "not a url" }], /malformed URL/);
});

test("mutation host guard does not expose credentials or query strings in sanitized output", () => {
  const sanitized = sanitizeMutationTargetForError({
    label: "ACCESS2_E2E_BASE_URL",
    url: "https://user:password@access2.salvardata.com/path?token=secret",
  });

  assert.equal(sanitized, "ACCESS2_E2E_BASE_URL: access2.salvardata.com");
  assert.doesNotMatch(sanitized, /password|token|secret|user/);
});

test("mutation host guard can allow explicit non-production staging hosts", () => {
  assert.doesNotThrow(() =>
    assertSafeMutationE2ETargets(
      [
        { label: "ACCESS2_E2E_BASE_URL", url: "https://staging.access2.example.test" },
        { label: "ACCESS2_E2E_API_BASE_URL", url: "https://api-staging.access2.example.test/api/v1" },
      ],
      {
        allowedNonLocalHosts: ["staging.access2.example.test", "api-staging.access2.example.test"],
      },
    ),
  );
});

test("mutation host guard blocks non-local targets without an allowlist", () => {
  assertBlocked(
    [{ label: "ACCESS2_E2E_BASE_URL", url: "https://staging.access2.example.test" }],
    /non-local host staging\.access2\.example\.test is not explicitly allowlisted/,
  );
});
