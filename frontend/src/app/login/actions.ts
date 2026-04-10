"use server";

import { redirect } from "next/navigation";

import { getApiBaseUrl } from "../../lib/api";
import { clearAuthToken, persistAuthToken } from "../../lib/auth/server-cookies";
import { redirectToLogin, resolveReturnPath } from "../../lib/auth/session";
import type { LoginRequest, TokenResponse } from "../../types/auth";

const REQUIRED_FIELDS_MESSAGE = "Email and password are required.";
const INVALID_CREDENTIALS_MESSAGE = "Invalid email or password.";
const GENERIC_ERROR_MESSAGE = "Unable to sign in right now. Please try again.";

function buildLoginErrorRedirect(errorMessage: string, nextPath?: string | null): never {
  const params = new URLSearchParams();
  params.set("error", errorMessage);
  if (nextPath) {
    params.set("next", nextPath);
  }
  redirect(`/login?${params.toString()}`);
}

export async function loginAction(formData: FormData): Promise<void> {
  console.log("loginAction invoked");

  const email = formData.get("email");
  const password = formData.get("password");
  const next = formData.get("next");
  const nextPath = typeof next === "string" ? next : null;

  console.log("raw form values", {
    emailType: typeof email,
    hasPassword: typeof password === "string" ? password.length > 0 : Boolean(password),
    nextPath,
  });

  if (typeof email !== "string" || typeof password !== "string" || !email.trim() || !password) {
    console.log("loginAction rejected: missing email or password");
    buildLoginErrorRedirect(REQUIRED_FIELDS_MESSAGE, nextPath);
  }

  const payload: LoginRequest = {
    email: email.trim(),
    password,
  };

  console.log("attempting login for", payload.email, "against", `${getApiBaseUrl()}/auth/login`);

  let redirectPath: string | null = null;

  try {
    const response = await fetch(`${getApiBaseUrl()}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    console.log("login response status", response.status, response.statusText);

    if (response.ok) {
      const data = (await response.json()) as TokenResponse;
      console.log("login succeeded, persisting auth token");
      await persistAuthToken(data.access_token);
      redirectPath = resolveReturnPath(nextPath);
    } else if (response.status === 401) {
      console.log("login failed: invalid credentials");
      await clearAuthToken();
      buildLoginErrorRedirect(INVALID_CREDENTIALS_MESSAGE, nextPath);
    } else {
      console.log("login failed: unexpected non-401 response");
      await clearAuthToken();
      buildLoginErrorRedirect(GENERIC_ERROR_MESSAGE, nextPath);
    }
  } catch (error) {
    console.error("loginAction fetch failed", error);
    await clearAuthToken();
    buildLoginErrorRedirect(GENERIC_ERROR_MESSAGE, nextPath);
  }

  redirect(redirectPath ?? "/patients");
}

export async function signOutAction() {
  await clearAuthToken();
  redirectToLogin();
}