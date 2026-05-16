import { expect, type APIRequestContext, type Page } from "@playwright/test";

export type DemoPatientLabel =
  | "Demo Patient 1"
  | "Demo Patient 2"
  | "Demo Patient 3"
  | "Demo Patient 4";

type TokenResponse = {
  access_token: string;
};

type UserResponse = {
  id: string;
  email: string;
};

export type WorklistItem = {
  patient_id: string;
  patient_display_name: string;
  total_events: number;
  latest_open_escalation_id: string | null;
  task_summary?: {
    open_task_count: number;
    in_progress_task_count: number;
    completed_tasks: number;
    completed_task_count?: number;
  } | null;
  workflow_status?: {
    label: string;
    has_active_work: boolean;
  } | null;
  next_step?: string | null;
  next_step_reason?: string | null;
};

type WorklistResponse = {
  items: WorklistItem[];
};

export type PatientAuditStatus = {
  patient_id: string;
  has_snapshot: boolean;
  latest_snapshot_id: string | null;
  review_status: string | null;
  assigned_reviewer_user_id?: string | null;
  review_state: {
    state: string;
    label: string;
    is_approvable: boolean;
    requires_override_for_approval: boolean;
    approval_override_used: boolean;
    missing_checklist_items: string[];
  } | null;
  audit_bundle: {
    available: boolean;
    exported: boolean;
    export_formats: string[];
  };
  next_step: {
    action: string;
    reason: string;
  };
  completion_summary: {
    status: string;
    missing_evidence_count: number;
    has_required_evidence: boolean;
    has_approval: boolean;
    has_export: boolean;
    reason: string;
  };
};

export type Snapshot = {
  id: string;
  patient_id: string;
  review_status: string;
  assigned_reviewer_user_id?: string | null;
  review_note: string | null;
  review_state: PatientAuditStatus["review_state"];
  packet_json: unknown;
  packet_markdown: string;
};

export type AuditBundle = {
  snapshot_id: string;
  patient_id: string;
  readiness_reasons: Array<{
    code: string;
    severity: string;
    label: string;
    detail: string;
  }>;
  audit_manifest: Record<string, unknown>;
  export_metadata: Record<string, unknown>;
};

export const LOCAL_V2_REJECTION_MUTATION_MARKER = "access2-local-v2-mutation:reviewer-rejection";

type SnapshotEventList = {
  events: Array<{
    event_type: string;
    metadata: Record<string, unknown>;
  }>;
};

const REQUIRED_ENV = ["ACCESS2_E2E_ADMIN_EMAIL", "ACCESS2_E2E_ADMIN_PASSWORD"] as const;

export function getApiBaseUrl(): string {
  if (process.env.ACCESS2_E2E_API_BASE_URL) {
    return trimTrailingSlash(process.env.ACCESS2_E2E_API_BASE_URL);
  }

  const frontendBaseUrl = trimTrailingSlash(process.env.ACCESS2_E2E_BASE_URL || "http://localhost:3000");
  const host = new URL(frontendBaseUrl).host;

  if (host === "access2.salvardata.com") {
    return "https://api.salvardata.com/api/v1";
  }
  if (host === "access2-frontend-production-c029.up.railway.app") {
    return "https://access2-backend-production-881f.up.railway.app/api/v1";
  }
  return "http://localhost:8000/api/v1";
}

export async function login(page: Page) {
  const missing = REQUIRED_ENV.filter((key) => !process.env[key]);
  if (missing.length > 0) {
    throw new Error(`Missing required E2E credential env vars: ${missing.join(", ")}`);
  }

  let loginResponseStatus: number | null = null;
  let loginResponseBody: string | null = null;

  page.on("response", async (response) => {
    if (!response.url().includes("/auth/login")) {
      return;
    }

    loginResponseStatus = response.status();
    const body = await response.text().catch(() => null);
    loginResponseBody = body ? sanitizeAuthResponseBody(body) : null;
  });

  await page.goto("/login");
  await page.getByLabel("Work email").fill(process.env.ACCESS2_E2E_ADMIN_EMAIL as string);
  await page.getByLabel("Password").fill(process.env.ACCESS2_E2E_ADMIN_PASSWORD as string);
  await page.getByRole("button", { name: "Sign in" }).click();

  try {
    await page.waitForURL((url) => !url.pathname.includes("/login"), {
      timeout: 150_000,
    });
  } catch {
    throw new Error(
      [
        "Login did not complete.",
        `Current URL: ${page.url()}`,
        `Auth response status: ${loginResponseStatus ?? "not observed"}`,
        `Auth response body: ${loginResponseBody ?? "not available"}`,
      ].join("\n"),
    );
  }

  await expect(page.getByRole("link", { name: "Patients" })).toBeVisible({
    timeout: 30_000,
  });
}

export async function getApiToken(request: APIRequestContext): Promise<string> {
  const missing = REQUIRED_ENV.filter((key) => !process.env[key]);
  if (missing.length > 0) {
    throw new Error(`Missing required E2E credential env vars: ${missing.join(", ")}`);
  }

  const response = await request.post(`${getApiBaseUrl()}/auth/login`, {
    data: {
      email: process.env.ACCESS2_E2E_ADMIN_EMAIL,
      password: process.env.ACCESS2_E2E_ADMIN_PASSWORD,
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  const payload = (await response.json()) as TokenResponse;
  return payload.access_token;
}

export async function getCurrentUser(request: APIRequestContext, token: string): Promise<UserResponse> {
  return apiGet<UserResponse>(request, token, "/auth/me");
}

export async function apiGet<T>(request: APIRequestContext, token: string, path: string): Promise<T> {
  const response = await request.get(`${getApiBaseUrl()}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()) as T;
}

export async function apiPatch<T>(
  request: APIRequestContext,
  token: string,
  path: string,
  data: Record<string, unknown>,
) {
  const response = await request.patch(`${getApiBaseUrl()}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    data,
  });
  return response;
}

export async function apiPost<T>(
  request: APIRequestContext,
  token: string,
  path: string,
  data: Record<string, unknown>,
): Promise<T> {
  const response = await request.post(`${getApiBaseUrl()}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    data,
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()) as T;
}

export async function findDemoPatient(
  request: APIRequestContext,
  token: string,
  label: DemoPatientLabel,
): Promise<WorklistItem | null> {
  const worklist = await getWorklist(request, token);
  return findWorklistItemByLabel(worklist.items, label);
}

export async function findDemoPatientCandidate(
  request: APIRequestContext,
  token: string,
  options: {
    label: DemoPatientLabel;
    patientIdEnv: string;
    matchesAuditStatus: (auditStatus: PatientAuditStatus) => boolean;
  },
): Promise<WorklistItem | null> {
  const worklist = await getWorklist(request, token);
  const byLabel = findWorklistItemByLabel(worklist.items, options.label);
  if (byLabel) {
    return byLabel;
  }

  const patientId = process.env[options.patientIdEnv];
  if (patientId) {
    return worklist.items.find((item) => item.patient_id === patientId) ?? null;
  }

  for (const item of worklist.items) {
    const auditStatus = await getPatientAuditStatus(request, token, item.patient_id);
    if (options.matchesAuditStatus(auditStatus)) {
      return item;
    }
  }
  return null;
}

export async function findLocalV2RejectionMutationPatient(
  request: APIRequestContext,
  token: string,
): Promise<WorklistItem | null> {
  const worklist = await getWorklist(request, token);
  const patientId = process.env.ACCESS2_LOCAL_V2_REJECTION_PATIENT_ID;
  if (patientId) {
    return worklist.items.find((item) => item.patient_id === patientId) ?? null;
  }

  return (
    worklist.items.find((item) =>
      item.patient_display_name.toLowerCase().includes("local v2 rejection mutation"),
    ) ?? null
  );
}

async function getWorklist(request: APIRequestContext, token: string): Promise<WorklistResponse> {
  const worklist = await apiGet<WorklistResponse>(
    request,
    token,
    "/patients/timeline/worklist-summary?active_only=false&limit=100",
  );
  return worklist;
}

function findWorklistItemByLabel(items: WorklistItem[], label: DemoPatientLabel) {
  return (
    items.find((item) => item.patient_display_name.toLowerCase().includes(label.toLowerCase())) ??
    null
  );
}

export async function getPatientAuditStatus(
  request: APIRequestContext,
  token: string,
  patientId: string,
) {
  return apiGet<PatientAuditStatus>(
    request,
    token,
    `/reports/access-review-packet/patients/${patientId}/audit-status`,
  );
}

export async function getSnapshot(request: APIRequestContext, token: string, snapshotId: string) {
  return apiGet<Snapshot>(request, token, `/reports/access-review-packet/snapshots/${snapshotId}`);
}

export async function getSnapshotEvents(request: APIRequestContext, token: string, snapshotId: string) {
  return apiGet<SnapshotEventList>(
    request,
    token,
    `/reports/access-review-packet/snapshots/${snapshotId}/events`,
  );
}

export async function exportAuditBundle(request: APIRequestContext, token: string, snapshotId: string) {
  return apiGet<AuditBundle>(
    request,
    token,
    `/reports/access-review-packet/snapshots/${snapshotId}/audit-bundle`,
  );
}

export async function verifyAuditManifest(
  request: APIRequestContext,
  token: string,
  snapshotId: string,
  auditManifest: Record<string, unknown>,
) {
  const response = await request.post(
    `${getApiBaseUrl()}/reports/access-review-packet/snapshots/${snapshotId}/audit-bundle/verify`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: { audit_manifest: auditManifest },
    },
  );
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()) as { verified: boolean; mismatches: unknown[] };
}

function trimTrailingSlash(value: string) {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function sanitizeAuthResponseBody(body: string): string {
  return body
    .replace(/"access_token"\s*:\s*"[^"]+"/g, '"access_token":"[redacted]"')
    .replace(/"token"\s*:\s*"[^"]+"/g, '"token":"[redacted]"')
    .replace(/Bearer\s+[A-Za-z0-9._~+/-]+=*/g, "Bearer [redacted]");
}
