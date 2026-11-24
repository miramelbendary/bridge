import "server-only";

import { unstable_rethrow } from "next/navigation";

import { ApiError } from "@/lib/api";

export type ActionResult<T = unknown> = { ok: true; data: T } | { ok: false; error: string; code?: string };

/** Run an API call inside a Server Action and turn failures into a displayable message.
 * Framework control flow (redirect / notFound) is re-thrown, never swallowed. */
export async function attempt<T>(fn: () => Promise<T>): Promise<ActionResult<T>> {
  try {
    return { ok: true, data: await fn() };
  } catch (error) {
    unstable_rethrow(error);
    if (error instanceof ApiError) {
      if (error.status === 403) return { ok: false, error: "You do not have permission to do that.", code: error.code };
      if (error.status === 429) return { ok: false, error: "Too many requests. Please wait a moment.", code: error.code };
      return { ok: false, error: error.detail, code: error.code };
    }
    return { ok: false, error: "Something went wrong. Please try again." };
  }
}

export function text(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

export type FormState = { error?: string; message?: string };
