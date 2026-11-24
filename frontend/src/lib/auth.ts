import "server-only";

import { notFound, redirect } from "next/navigation";

import { ApiError, apiFetch, type CurrentUser, type FetchOptions, type Role } from "./api";
import { getSessionToken } from "./session";

/**
 * Data Access Layer: the single place that turns the session cookie into authenticated API
 * calls. The backend re-validates the token and the user's role on every request; the frontend
 * never makes authorization decisions on its own (it only hides navigation for convenience).
 */
export async function api<T>(path: string, opts: Omit<FetchOptions, "token"> = {}): Promise<T> {
  const token = await getSessionToken();
  if (!token) redirect("/login");
  try {
    return await apiFetch<T>(path, { ...opts, token });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/login?expired=1");
    if (error instanceof ApiError && error.status === 404 && (opts.method ?? "GET") === "GET") notFound();
    throw error;
  }
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return api<CurrentUser>("/api/v1/users/me");
}

export async function requireRole(...roles: Role[]): Promise<CurrentUser> {
  const user = await getCurrentUser();
  if (!roles.includes(user.role)) notFound();
  return user;
}
