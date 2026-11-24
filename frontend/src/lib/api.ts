import "server-only";

/**
 * Server-side client for the BRIDGE FastAPI backend.
 * BRIDGE_API_URL is a server-only variable: the browser never talks to the backend directly.
 */
const API_URL = (process.env.BRIDGE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const TIMEOUT_MS = 10_000;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`API ${status}: ${detail}`);
  }
}

export type Specialization = {
  id: string;
  code: string;
  name: string;
  description: string;
};

export type Role = "student" | "professor" | "admin";

export type CurrentUser = {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  permissions: string[];
  profile: { display_name: string; specialization: Specialization | null } | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
};

function detailFrom(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: a list of { msg, loc }.
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d)))
        .join("; ");
    }
  }
  return fallback;
}

export async function apiFetch<T>(
  path: string,
  { token, method = "GET", body }: { token?: string; method?: string; body?: unknown } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    throw new ApiError(503, "The BRIDGE service is unreachable. Please try again shortly.");
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, detailFrom(data, response.statusText || "Request failed"));
  }
  return data as T;
}
