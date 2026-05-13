import { NextResponse } from "next/server";

import { getApiBaseUrl } from "../../../../lib/api";
import { getAuthTokenFromCookies } from "../../../../lib/auth/server-cookies";

type RouteContext = {
  params: Promise<{
    snapshotId: string;
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

export async function POST(_request: Request, { params }: RouteContext) {
  const { snapshotId } = await params;
  const normalizedSnapshotId = typeof snapshotId === "string" ? snapshotId.trim() : "";
  if (!normalizedSnapshotId) {
    return NextResponse.json({ error: "Snapshot ID is required." }, { status: 400 });
  }

  const authToken = await getAuthTokenFromCookies();
  if (!authToken) {
    return NextResponse.json({ error: "Sign in is required to approve a review packet snapshot." }, { status: 401 });
  }

  const baseUrl = getApiBaseUrl();
  const snapshotPath = encodeURIComponent(normalizedSnapshotId);
  const upstreamUrl = `${baseUrl}/reports/access-review-packet/snapshots/${snapshotPath}/review`;
  const upstreamResponse = await fetch(upstreamUrl, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      review_status: "approved",
    }),
    cache: "no-store",
  });

  const payload = await parseJsonResponse(upstreamResponse);
  if (!upstreamResponse.ok) {
    return NextResponse.json(
      {
        error: toErrorMessage(payload, "Review packet snapshot approval failed."),
      },
      { status: upstreamResponse.status },
    );
  }

  const persistedReviewStatus =
    payload && typeof payload === "object" && "review_status" in payload
      ? (payload as { review_status?: unknown }).review_status
      : undefined;
  if (persistedReviewStatus !== "approved") {
    return NextResponse.json(
      {
        error: "Review packet snapshot approval did not persist.",
      },
      { status: 502 },
    );
  }

  return NextResponse.json(payload, { status: upstreamResponse.status });
}
