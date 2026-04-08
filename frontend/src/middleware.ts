import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "./lib/auth/constants";

const LOGIN_PATH = "/login";
const DEFAULT_AFTER_LOGIN_PATH = "/patients";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get(AUTH_COOKIE_NAME)?.value);

  const isLoginRoute = pathname === LOGIN_PATH;
  const isProtectedRoute = pathname.startsWith("/patients");

  if (!hasSession && isProtectedRoute) {
    const loginUrl = new URL(LOGIN_PATH, request.url);
    return NextResponse.redirect(loginUrl);
  }

  if (hasSession && isLoginRoute) {
    const targetUrl = new URL(DEFAULT_AFTER_LOGIN_PATH, request.url);
    return NextResponse.redirect(targetUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/login", "/patients/:path*"],
};
