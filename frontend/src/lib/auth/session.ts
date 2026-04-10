import { redirect } from "next/navigation";

import { getAuthTokenFromCookies } from "./server-cookies";

export const DEFAULT_RETURN_PATH = "/patients";

const isSafeRelativePath = (value: string) =>
  value.startsWith("/") && !value.startsWith("//");

export function sanitizeReturnPath(raw?: string | null): string | null {
  if (typeof raw !== "string") {
    return null;
  }
  const trimmed = raw.trim();
  if (!trimmed || !isSafeRelativePath(trimmed)) {
    return null;
  }
  return trimmed;
}

export function resolveReturnPath(raw?: string | null): string {
  return sanitizeReturnPath(raw) ?? DEFAULT_RETURN_PATH;
}

export function buildLoginRedirectUrl(rawNext?: string | null): string {
  const nextPath = resolveReturnPath(rawNext);
  return `/login?next=${encodeURIComponent(nextPath)}`;
}

export function redirectToLogin(rawNext?: string | null): never {
  const url = buildLoginRedirectUrl(rawNext);
  console.log("[session.redirectToLogin]", { rawNext, url });
  redirect(url);
}

export async function requireAuth(rawNext?: string | null): Promise<string> {
  const token = await getAuthTokenFromCookies();
  console.log("[session.requireAuth]", {
    rawNext,
    hasToken: Boolean(token),
    tokenLength: token?.length ?? 0,
  });

  if (!token) {
    redirectToLogin(rawNext);
  }

  return token;
}

export function handleUnauthorized(rawNext?: string | null): never {
  console.log("[session.handleUnauthorized]", { rawNext });
  redirectToLogin(rawNext);
}