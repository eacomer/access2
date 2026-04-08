import { redirect } from "next/navigation";

import { clearAuthToken, getAuthTokenFromCookies } from "./auth/server-cookies";

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
  const authToken = getAuthTokenFromCookies();
  if (authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }

  const response = await fetch(url, {
    ...options.init,
    headers,
    cache: "no-store",
    credentials: "include",
  });

  if (response.status === 401) {
    clearAuthToken();
    redirect("/login");
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
): Promise<PatientTimelineWorklistSummaryResponse> {
  return apiFetch<PatientTimelineWorklistSummaryResponse>("/patients/timeline/worklist-summary", {
    query: {
      skip: params.skip,
      limit: params.limit,
      active_only: params.activeOnly,
      has_unread_events: params.hasUnreadEvents,
      ...(params.patientIds?.length ? { patient_ids: params.patientIds } : {}),
    },
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
  });
}

export async function fetchPatientTimelineEvent(
  patientId: string,
  eventId: string,
): Promise<PatientTimelineDetailResponse> {
  return apiFetch<PatientTimelineDetailResponse>(`/patients/${patientId}/timeline/${eventId}`);
}

export async function fetchEscalation(escalationId: string): Promise<PatientEscalation> {
  return apiFetch<PatientEscalation>(`/escalations/${escalationId}`);
}

export async function acknowledgeEscalation(escalationId: string): Promise<PatientEscalation> {
  return apiFetch<PatientEscalation>(`/escalations/${escalationId}/acknowledge`, {
    init: {
      method: "POST",
    },
  });
}

export async function updateEscalationStatus(
  escalationId: string,
  payload: { status: EscalationStatus; note?: string | null },
): Promise<PatientEscalation> {
  return apiFetch<PatientEscalation>(`/escalations/${escalationId}/status`, {
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  });
}

export async function resolveEscalation(
  escalationId: string,
  payload: { resolution_notes?: string | null } = {},
): Promise<PatientEscalation> {
  return apiFetch<PatientEscalation>(`/escalations/${escalationId}/resolve`, {
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  });
}

export async function createInterventionTask(
  escalationId: string,
  payload: InterventionTaskCreateRequest,
): Promise<InterventionTask> {
  return apiFetch<InterventionTask>(`/escalations/${escalationId}/tasks`, {
    init: {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  });
}
