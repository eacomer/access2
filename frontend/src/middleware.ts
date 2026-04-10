import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "./lib/auth/server-cookies";

const LOGIN_PATH = "/login";

const isProtectedPath = (pathname: string) =>
  pathname.startsWith("/patients") || pathname.startsWith("/admin");

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get(AUTH_COOKIE_NAME)?.value);

  const isLoginRoute = pathname === LOGIN_PATH;
  const isProtectedRoute = isProtectedPath(pathname);

  if (!hasSession && isProtectedRoute) {
    const loginUrl = new URL(LOGIN_PATH, request.url);
    const nextPath = `${pathname}${search ?? ""}`;
    loginUrl.searchParams.set("next", nextPath);
    return NextResponse.redirect(loginUrl);
  }

  if (isLoginRoute) {
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/login", "/patients/:path*", "/admin/:path*"],
};
