import { NextRequest, NextResponse } from "next/server";

import { getApiBaseUrl } from "../../../../../lib/api";
import { getAuthTokenFromCookies } from "../../../../../lib/auth/server-cookies";

type RouteContext = {
  params: Promise<{
    patientId: string;
  }>;
};

const toErrorMessage = (payload: unknown, fallback: string) => {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length) {
      return detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }
          if (item && typeof item === "object" && "msg" in item) {
            const message = (item as { msg?: unknown }).msg;
            return typeof message === "string" ? message : null;
          }
          return null;
        })
        .filter(Boolean)
        .join(" ");
    }
  }
  if (payload && typeof payload === "object" && "error" in payload) {
    const error = (payload as { error?: unknown }).error;
    if (typeof error === "string" && error.trim()) {
      return error;
    }
  }
  return fallback;
};

const parseJsonResponse = async (response: Response) => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

export const dynamic = "force-dynamic";

export async function POST(_request: NextRequest, { params }: RouteContext) {
  const { patientId } = await params;
  const normalizedPatientId = typeof patientId === "string" ? patientId.trim() : "";
  if (!normalizedPatientId) {
    return NextResponse.json({ error: "Patient ID is required." }, { status: 400 });
  }

  const authToken = await getAuthTokenFromCookies();
  if (!authToken) {
    return NextResponse.json(
      { error: "Sign in is required to create a review packet snapshot." },
      { status: 401 },
    );
  }

  const baseUrl = getApiBaseUrl();
  const patientPath = encodeURIComponent(normalizedPatientId);
  const upstreamUrl = `${baseUrl}/reports/access-review-packet/${patientPath}/snapshots`;
  const upstreamResponse = await fetch(upstreamUrl, {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    cache: "no-store",
  });

  const payload = await parseJsonResponse(upstreamResponse);
  if (!upstreamResponse.ok) {
    return NextResponse.json(
      {
        error: toErrorMessage(payload, "Review packet snapshot creation failed."),
      },
      { status: upstreamResponse.status },
    );
  }

  return NextResponse.json(payload, { status: upstreamResponse.status });
}
