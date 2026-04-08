import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME } from "./constants";

const isProduction = process.env.NODE_ENV === "production";
const BASE_COOKIE_OPTIONS = {
  name: AUTH_COOKIE_NAME,
  httpOnly: true,
  sameSite: "lax" as const,
  secure: isProduction,
  path: "/",
};

export function getAuthTokenFromCookies(): string | null {
  return cookies().get(AUTH_COOKIE_NAME)?.value ?? null;
}

export function persistAuthToken(token: string) {
  cookies().set({ ...BASE_COOKIE_OPTIONS, value: token });
}

export function clearAuthToken() {
  cookies().delete(AUTH_COOKIE_NAME);
}
