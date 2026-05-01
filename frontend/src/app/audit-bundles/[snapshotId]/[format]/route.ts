import { NextRequest, NextResponse } from "next/server";

import { getAuthTokenFromCookies } from "../../../../lib/auth/server-cookies";
import { buildLoginRedirectUrl } from "../../../../lib/auth/session";
import { getApiBaseUrl } from "../../../../lib/api";

type AuditBundleFormat = "json" | "markdown" | "pdf";

type RouteContext = {
  params: Promise<{
    snapshotId: string;
    format: string;
  }>;
};

const DOWNLOAD_FORMATS: Record<
  AuditBundleFormat,
  {
    endpointSuffix: string;
    accept: string;
    contentType: string;
    extension: string;
  }
> = {
  json: {
    endpointSuffix: "",
    accept: "application/json",
    contentType: "application/json",
    extension: "json",
  },
  markdown: {
    endpointSuffix: "/markdown",
    accept: "text/markdown",
    contentType: "text/markdown; charset=utf-8",
    extension: "md",
  },
  pdf: {
    endpointSuffix: "/pdf",
    accept: "application/pdf",
    contentType: "application/pdf",
    extension: "pdf",
  },
};

const isAuditBundleFormat = (value: string): value is AuditBundleFormat =>
  Object.prototype.hasOwnProperty.call(DOWNLOAD_FORMATS, value);

const getSafeFilenameSnapshotId = (snapshotId: string) =>
  snapshotId.replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "snapshot";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest, { params }: RouteContext) {
  const { snapshotId, format } = await params;

  if (!isAuditBundleFormat(format)) {
    return NextResponse.json({ error: "Unsupported audit bundle format." }, { status: 404 });
  }

  const authToken = await getAuthTokenFromCookies();
  if (!authToken) {
    return NextResponse.redirect(new URL(buildLoginRedirectUrl(request.nextUrl.pathname), request.url));
  }

  const downloadFormat = DOWNLOAD_FORMATS[format];
  const baseUrl = getApiBaseUrl();
  const snapshotPath = encodeURIComponent(snapshotId);
  const upstreamUrl = `${baseUrl}/reports/access-review-packet/snapshots/${snapshotPath}/audit-bundle${downloadFormat.endpointSuffix}`;

  const upstreamResponse = await fetch(upstreamUrl, {
    headers: {
      Accept: downloadFormat.accept,
      Authorization: `Bearer ${authToken}`,
    },
    cache: "no-store",
  });

  if (upstreamResponse.status === 401) {
    return NextResponse.redirect(new URL(buildLoginRedirectUrl(request.nextUrl.pathname), request.url));
  }

  if (!upstreamResponse.ok) {
    const body = await upstreamResponse.text();
    return new NextResponse(body || "Audit bundle download failed.", {
      status: upstreamResponse.status,
      headers: {
        "Content-Type": upstreamResponse.headers.get("Content-Type") ?? "text/plain; charset=utf-8",
      },
    });
  }

  const headers = new Headers();
  headers.set("Content-Type", upstreamResponse.headers.get("Content-Type") ?? downloadFormat.contentType);
  headers.set(
    "Content-Disposition",
    upstreamResponse.headers.get("Content-Disposition") ??
      `attachment; filename="access2-audit-bundle-${getSafeFilenameSnapshotId(snapshotId)}.${downloadFormat.extension}"`,
  );

  const body = await upstreamResponse.arrayBuffer();
  return new NextResponse(body, {
    status: upstreamResponse.status,
    headers,
  });
}
