import { expect, test, type Page, type Request } from "@playwright/test";

import { login } from "./helpers/access2";

const PRODUCTION_FRONTEND_URL = "https://access2.salvardata.com";
const ALLOWED_WRITE_PATHS = ["/login"];
const FORBIDDEN_PATH_PATTERNS = [
  /\/audit-bundles?\//i,
  /\/audit-bundle(?:\/|$)/i,
  /\/assignment(?:\/|$)/i,
  /\/approve(?:\/|$)/i,
  /\/reject(?:\/|$)/i,
  /\/review(?:\/|$)/i,
  /\/create-snapshot(?:\/|$)/i,
  /\/verify(?:\/|$)/i,
];
const MUTATION_CONTROL_NAME = /approve|reject|assign|override|export|download|create snapshot|verify manifest/i;

function assertProductionBaseUrl() {
  const baseUrl = process.env.ACCESS2_E2E_BASE_URL ?? PRODUCTION_FRONTEND_URL;
  const parsed = new URL(baseUrl);
  expect(parsed.origin).toBe(PRODUCTION_FRONTEND_URL);
}

function isAllowedWriteRequest(request: Request) {
  const url = new URL(request.url());
  return request.method() === "POST" && ALLOWED_WRITE_PATHS.includes(url.pathname);
}

async function installReadOnlyRequestGuard(page: Page) {
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();

    if (FORBIDDEN_PATH_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
      throw new Error(`Read-only smoke blocked forbidden request: ${method} ${url.pathname}`);
    }

    if (!["GET", "HEAD", "OPTIONS"].includes(method) && !isAllowedWriteRequest(request)) {
      throw new Error(`Read-only smoke blocked unexpected write request: ${method} ${url.pathname}`);
    }

    await route.continue();
  });
}

test.describe("ACCESS2 production read-only stakeholder smoke", () => {
  test.beforeEach(async ({ page }) => {
    assertProductionBaseUrl();
    await installReadOnlyRequestGuard(page);
  });

  test("Demo Guide shows deployed stakeholder clarity copy without data-changing calls", async ({ page }) => {
    await login(page);

    await page.getByRole("link", { name: "Demo Guide" }).click();
    await expect(page).toHaveURL(/\/demo-guide$/);

    const pageRoot = page.getByTestId("demo-guide-page");
    await expect(pageRoot).toBeVisible();
    await expect(pageRoot.getByRole("heading", { name: "Demo Guide" })).toBeVisible();

    await expect(pageRoot).toContainText("ACCESS2 is not just a worklist");
    await expect(pageRoot).toContainText("care update");
    await expect(pageRoot).toContainText("resolution");
    await expect(pageRoot).toContainText("8 passed, 2 skipped, 0 failed");
    await expect(pageRoot).toContainText("V2 correction-loop mutation stays localhost-only");
    await expect(pageRoot).toContainText("This page is read-only guidance and does not create or mutate workflow data.");

    await expect(pageRoot.getByRole("button", { name: MUTATION_CONTROL_NAME })).toHaveCount(0);
    await expect(pageRoot.getByRole("link", { name: /Download JSON|Download Markdown|Download PDF/i })).toHaveCount(0);
  });
});
