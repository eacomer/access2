import { cookies, headers } from "next/headers";

export const AUTH_COOKIE_NAME = "access_token";

const ONE_DAY_IN_SECONDS = 60 * 60 * 24;

const isSecureRequest = async (): Promise<boolean> => {
  const headerStore = await headers();

  const forwardedProto = headerStore.get("x-forwarded-proto");
  if (forwardedProto) {
    const primaryProto = forwardedProto.split(",")[0]?.trim().toLowerCase();
    if (primaryProto) {
      return primaryProto === "https";
    }
  }

  const forwarded = headerStore.get("forwarded");
  if (forwarded) {
    const protoMatch = forwarded.match(/proto=([^;,\s]+)/i);
    if (protoMatch?.[1]) {
      return protoMatch[1].trim().toLowerCase() === "https";
    }
  }

  return process.env.NODE_ENV === "production";
};

export async function getAuthTokenFromCookies(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIE_NAME)?.value ?? null;
}

export async function persistAuthToken(token: string) {
  const cookieStore = await cookies();
  cookieStore.set(AUTH_COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: await isSecureRequest(),
    path: "/",
    maxAge: ONE_DAY_IN_SECONDS,
  });
}

export async function clearAuthToken() {
  const cookieStore = await cookies();
  cookieStore.delete(AUTH_COOKIE_NAME);
}