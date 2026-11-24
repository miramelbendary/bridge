"use server";

import { redirect } from "next/navigation";

import { ApiError, apiFetch, type TokenResponse } from "@/lib/api";
import { clearSessionToken, setSessionToken } from "@/lib/session";

export type AuthFormState = { error?: string; email?: string; displayName?: string };

function field(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return "Email/password sign-in is disabled on this deployment.";
    if (error.status === 429) return "Too many attempts. Please wait a minute and try again.";
    return error.detail;
  }
  return "Something went wrong. Please try again.";
}

export async function loginAction(_prev: AuthFormState, formData: FormData): Promise<AuthFormState> {
  const email = field(formData, "email");
  const password = formData.get("password");
  if (!email || typeof password !== "string" || !password) {
    return { error: "Enter your email and password.", email };
  }
  try {
    const result = await apiFetch<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    });
    await setSessionToken(result.access_token, result.expires_in);
  } catch (error) {
    return { error: messageFor(error), email };
  }
  redirect("/dashboard");
}

export async function registerAction(
  _prev: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const email = field(formData, "email");
  const displayName = field(formData, "display_name");
  const password = formData.get("password");
  const confirm = formData.get("confirm_password");
  if (!email || !displayName || typeof password !== "string") {
    return { error: "All fields are required.", email, displayName };
  }
  if (password.length < 10) {
    return { error: "Password must be at least 10 characters.", email, displayName };
  }
  if (password !== confirm) {
    return { error: "Passwords do not match.", email, displayName };
  }
  try {
    const result = await apiFetch<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: { email, password, display_name: displayName },
    });
    await setSessionToken(result.access_token, result.expires_in);
  } catch (error) {
    return { error: messageFor(error), email, displayName };
  }
  redirect("/dashboard");
}

export async function logoutAction(): Promise<void> {
  await clearSessionToken();
  redirect("/login");
}
