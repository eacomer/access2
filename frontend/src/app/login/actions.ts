"use server";

import { redirect } from "next/navigation";

import { getApiBaseUrl } from "../../lib/api";
import { clearAuthToken, persistAuthToken } from "../../lib/auth/server-cookies";
import type { LoginRequest, TokenResponse } from "../../types/auth";

export type LoginActionState = {
  error?: string;
};

const REQUIRED_FIELDS_MESSAGE = "Email and password are required.";
const INVALID_CREDENTIALS_MESSAGE = "Invalid email or password.";
const GENERIC_ERROR_MESSAGE = "Unable to sign in right now. Please try again.";

export async function loginAction(_prevState: LoginActionState, formData: FormData): Promise<LoginActionState> {
  const email = formData.get("email");
  const password = formData.get("password");

  if (typeof email !== "string" || typeof password !== "string" || !email.trim() || !password) {
    return { error: REQUIRED_FIELDS_MESSAGE };
  }

  const payload: LoginRequest = {
    email: email.trim(),
    password,
  };

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

    if (response.ok) {
      const data = (await response.json()) as TokenResponse;
      persistAuthToken(data.access_token);
      redirect("/patients");
    }

    if (response.status === 401) {
      clearAuthToken();
      return { error: INVALID_CREDENTIALS_MESSAGE };
    }
  } catch {
    clearAuthToken();
    return { error: GENERIC_ERROR_MESSAGE };
  }

  clearAuthToken();
  return { error: GENERIC_ERROR_MESSAGE };
}
