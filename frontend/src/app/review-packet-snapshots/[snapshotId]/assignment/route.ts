import { NextRequest, NextResponse } from "next/server";

import { getApiBaseUrl } from "../../../../lib/api";
import { getAuthTokenFromCookies } from "../../../../lib/auth/server-cookies";

type RouteContext = {
  params: Promise<{
    snapshotId: string;
  }>;
};

type AssignSnapshotRequestBody = {
  assignedReviewerUserId?: unknown;
  assigned_reviewer_user_id?: unknown;
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

export async function POST(request: NextRequest, { params }: RouteContext) {
  const { snapshotId } = await params;
  const normalizedSnapshotId = typeof snapshotId === "string" ? snapshotId.trim() : "";
  if (!normalizedSnapshotId) {
    return NextResponse.json({ error: "Snapshot ID is required." }, { status: 400 });
  }

  let body: AssignSnapshotRequestBody;
  try {
    body = (await request.json()) as AssignSnapshotRequestBody;
  } catch {
    return NextResponse.json({ error: "Invalid assignment request JSON." }, { status: 400 });
  }

  const rawReviewerUserId = body.assignedReviewerUserId ?? body.assigned_reviewer_user_id;
  const assignedReviewerUserId = typeof rawReviewerUserId === "string" ? rawReviewerUserId.trim() : "";
  if (!assignedReviewerUserId) {
    return NextResponse.json({ error: "Reviewer user ID required." }, { status: 400 });
  }

  const authToken = await getAuthTokenFromCookies();
  if (!authToken) {
    return NextResponse.json({ error: "Sign in is required to assign a review packet snapshot." }, { status: 401 });
  }

  const baseUrl = getApiBaseUrl();
  const snapshotPath = encodeURIComponent(normalizedSnapshotId);
  const upstreamUrl = `${baseUrl}/reports/access-review-packet/snapshots/${snapshotPath}/assignment`;
  const upstreamResponse = await fetch(upstreamUrl, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      assigned_reviewer_user_id: assignedReviewerUserId,
    }),
    cache: "no-store",
  });

  const payload = await parseJsonResponse(upstreamResponse);
  if (!upstreamResponse.ok) {
    return NextResponse.json(
      {
        error: toErrorMessage(payload, "Review packet snapshot assignment failed."),
      },
      { status: upstreamResponse.status },
    );
  }

  const persistedReviewerUserId =
    payload && typeof payload === "object" && "assigned_reviewer_user_id" in payload
      ? (payload as { assigned_reviewer_user_id?: unknown }).assigned_reviewer_user_id
      : undefined;
  if (persistedReviewerUserId !== assignedReviewerUserId) {
    return NextResponse.json(
      {
        error: "Review packet snapshot assignment did not persist.",
      },
      { status: 502 },
    );
  }

  return NextResponse.json(payload, { status: upstreamResponse.status });
}
