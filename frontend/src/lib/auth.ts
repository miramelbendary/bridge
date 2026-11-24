import "server-only";

import { redirect } from "next/navigation";

import { ApiError, apiFetch, type CurrentUser, type Specialization } from "./api";
import { getSessionToken } from "./session";

/**
 * Data Access Layer: the single place that turns the session cookie into a verified user.
 * The backend re-validates the token and the user's role on every request; the frontend never
 * makes authorization decisions on its own.
 */
export async function getCurrentUser(): Promise<CurrentUser> {
  const token = await getSessionToken();
  if (!token) redirect("/login");
  try {
    return await apiFetch<CurrentUser>("/api/v1/users/me", { token });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/login?expired=1");
    throw error;
  }
}

export async function getSpecializations(): Promise<Specialization[]> {
  const token = await getSessionToken();
  if (!token) redirect("/login");
  return apiFetch<Specialization[]>("/api/v1/specializations", { token });
}
