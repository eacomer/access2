import { getAuthTokenFromCookies } from "./auth/server-cookies";
import { handleUnauthorized } from "./auth/session";

import type {
  WorkflowBootstrapCreateRequest,
  WorkflowBootstrapCreateResponse,
} from "../types/admin";
import type {
  PatientEscalation,
  PatientTimelineDetailResponse,
  PatientTimelineListResponse,
  PatientTimelineWorklistSummaryResponse,
  PatientTimelineFilters,
  EscalationStatus,
  InterventionTask,
  InterventionTaskCreateRequest,
} from "../types/patient";

const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

type QueryValue = string | number | boolean | Array<string | number | boolean> | undefined | null;

type ApiFetchOptions = {
  query?: Record<string, QueryValue>;
  init?: RequestInit;
  auth?: {
    redirectPath?: string | null;
  };
};

type AuthenticatedRequestOptions = {
  authRedirectPath?: string | null;
};

const normalizeBaseUrl = (value?: string) => {
  if (!value || value.trim().length === 0) {
    return DEFAULT_API_BASE_URL;
  }
  return value.endsWith("/") ? value.slice(0, -1) : value;
};

export const getApiBaseUrl = () => normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

async function apiFetch<TResponse>(path: string, options: ApiFetchOptions = {}): Promise<TResponse> {
  const base = getApiBaseUrl();
  const relativePath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${base}${relativePath}`);

  if (options.query) {
    for (const [key, rawValue] of Object.entries(options.query)) {
      if (rawValue === undefined || rawValue === null) {
        continue;
      }
      if (Array.isArray(rawValue)) {
        rawValue.forEach((value) => url.searchParams.append(key, String(value)));
      } else {
        url.searchParams.set(key, String(rawValue));
      }
    }
  }

  const headers = new Headers(options.init?.headers);
  headers.set("Accept", "application/json");

  const authToken = await getAuthTokenFromCookies();
  console.log("[apiFetch.request]", {
    path,
    url: url.toString(),
    hasAuthToken: Boolean(authToken),
    authTokenLength: authToken?.length ?? 0,
    redirectPath: options.auth?.redirectPath ?? null,
  });

  if (authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }

  const response = await fetch(url, {
    ...options.init,
    headers,
    cache: "no-store",
    credentials: "include",
  });

  console.log("[apiFetch.response]", {
    path,
    status: response.status,
    statusText: response.statusText,
    redirected: response.redirected,
  });

  if (response.status === 401) {
    return handleUnauthorized(options.auth?.redirectPath);
  }

  if (!response.ok) {
    const message = `Request failed for ${url.pathname}: ${response.status} ${response.statusText}`;
    throw new Error(message);
  }

  return (await response.json()) as TResponse;
}

export async function fetchWorklistSummary(
  params: {
    skip?: number;
    limit?: number;
    patientIds?: string[];
    hasUnreadEvents?: boolean;
    activeOnly?: boolean;
  } = {},
  options: AuthenticatedRequestOptions = {},
): Promise<PatientTimelineWorklistSummaryResponse> {
  return apiFetch<PatientTimelineWorklistSummaryResponse>("/patients/timeline/worklist-summary", {
    query: {
      skip: params.skip,
      limit: params.limit,
      active_only: params.activeOnly,
      has_unread_events: params.hasUnreadEvents,
      ...(params.patientIds?.length ? { patient_ids: params.patientIds } : {}),
    },
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function fetchPatientTimeline(
  patientId: string,
  options: {
    limit?: number;
    cursorOccurredAt?: string;
    cursorEventId?: string;
    filters?: PatientTimelineFilters;
  } = {},
  requestOptions: AuthenticatedRequestOptions = {},
): Promise<PatientTimelineListResponse> {
  const query: Record<string, QueryValue> = {
    limit: options.limit,
    cursor_occurred_at: options.cursorOccurredAt,
    cursor_event_id: options.cursorEventId,
  };

  if (options.filters) {
    const { filters } = options;
    if (filters.event_types?.length) {
      query.event_types = filters.event_types;
    }
    if (filters.occurred_after) {
      query.occurred_after = filters.occurred_after;
    }
    if (filters.occurred_before) {
      query.occurred_before = filters.occurred_before;
    }
    if (filters.related_escalation_id) {
      query.related_escalation_id = filters.related_escalation_id;
    }
    if (filters.related_task_id) {
      query.related_task_id = filters.related_task_id;
    }
    if (filters.task_statuses?.length) {
      query.task_statuses = filters.task_statuses;
    }
    if (filters.include_only_open_work) {
      query.include_only_open_work = filters.include_only_open_work;
    }
  }

  return apiFetch<PatientTimelineListResponse>(`/patients/${patientId}/timeline`, {
    query,
    auth: { redirectPath: requestOptions.authRedirectPath },
  });
}

export async function fetchPatientTimelineEvent(
  patientId: string,
  eventId: string,
  options: AuthenticatedRequestOptions = {},
): Promise<PatientTimelineDetailResponse> {
  return apiFetch<PatientTimelineDetailResponse>(`/patients/${patientId}/timeline/${eventId}`, {
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function fetchEscalation(
  escalationId: string,
  options: AuthenticatedRequestOptions = {},
): Promise<PatientEscalation> {
  return apiFetch<PatientEscalation>(`/escalations/${escalationId}`, {
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function acknowledgeEscalation(
  escalationId: string,
  options: AuthenticatedRequestOptions = {},
): Promise<PatientEscalation> {
  return apiFetch<PatientEscalation>(`/escalations/${escalationId}/acknowledge`, {
    init: {
      method: "POST",
    },
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function updateEscalationStatus(
  escalationId: string,
  payload: { status: EscalationStatus; note?: string | null },
  options: AuthenticatedRequestOptions = {},
): Promise<PatientEscalation> {
  return apiFetch<PatientEscalation>(`/escalations/${escalationId}/status`, {
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function resolveEscalation(
  escalationId: string,
  payload: { resolution_notes?: string | null } = {},
  options: AuthenticatedRequestOptions = {},
): Promise<PatientEscalation> {
  return apiFetch<PatientEscalation>(`/escalations/${escalationId}/resolve`, {
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function createInterventionTask(
  escalationId: string,
  payload: InterventionTaskCreateRequest,
  options: AuthenticatedRequestOptions = {},
): Promise<InterventionTask> {
  return apiFetch<InterventionTask>(`/escalations/${escalationId}/tasks`, {
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function fetchInterventionTask(
  taskId: string,
  options: AuthenticatedRequestOptions = {},
): Promise<InterventionTask> {
  return apiFetch<InterventionTask>(`/tasks/${taskId}`, {
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function startInterventionTask(
  taskId: string,
  options: AuthenticatedRequestOptions = {},
): Promise<InterventionTask> {
  return apiFetch<InterventionTask>(`/tasks/${taskId}/start`, {
    init: {
      method: "POST",
    },
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function completeInterventionTask(
  taskId: string,
  payload: { completion_note?: string | null } = {},
  options: AuthenticatedRequestOptions = {},
): Promise<InterventionTask> {
  return apiFetch<InterventionTask>(`/tasks/${taskId}/complete`, {
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    auth: { redirectPath: options.authRedirectPath },
  });
}

export async function createWorkflowBootstrap(
  payload: WorkflowBootstrapCreateRequest,
  options: AuthenticatedRequestOptions = {},
): Promise<WorkflowBootstrapCreateResponse> {
  return apiFetch<WorkflowBootstrapCreateResponse>("/admin/workflow/bootstrap", {
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
    auth: { redirectPath: options.authRedirectPath },
  });
}
