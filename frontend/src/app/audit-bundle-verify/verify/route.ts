import { NextRequest, NextResponse } from "next/server";

import { getApiBaseUrl } from "../../../lib/api";
import { getAuthTokenFromCookies } from "../../../lib/auth/server-cookies";

type VerifyRequestBody = {
  snapshotId?: unknown;
  auditManifest?: unknown;
};

const toErrorMessage = (payload: unknown, fallback: string) => {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return fallback;
};

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const authToken = await getAuthTokenFromCookies();
  if (!authToken) {
    return NextResponse.json({ error: "Sign in is required to verify an audit bundle." }, { status: 401 });
  }

  let body: VerifyRequestBody;
  try {
    body = (await request.json()) as VerifyRequestBody;
  } catch {
    return NextResponse.json({ error: "Invalid verification request JSON." }, { status: 400 });
  }

  const snapshotId = typeof body.snapshotId === "string" ? body.snapshotId.trim() : "";
  if (!snapshotId) {
    return NextResponse.json({ error: "Snapshot ID is required." }, { status: 400 });
  }
  if (!body.auditManifest || typeof body.auditManifest !== "object" || Array.isArray(body.auditManifest)) {
    return NextResponse.json({ error: "auditManifest must be a JSON object." }, { status: 400 });
  }

  const upstreamUrl = `${getApiBaseUrl()}/reports/access-review-packet/snapshots/${encodeURIComponent(
    snapshotId,
  )}/audit-bundle/verify`;

  const upstreamResponse = await fetch(upstreamUrl, {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      audit_manifest: body.auditManifest,
    }),
    cache: "no-store",
  });

  const payload = await upstreamResponse.json().catch(() => null);

  if (!upstreamResponse.ok) {
    return NextResponse.json(
      {
        error: toErrorMessage(payload, "Audit bundle verification failed."),
      },
      { status: upstreamResponse.status },
    );
  }

  return NextResponse.json(payload, { status: upstreamResponse.status });
}
