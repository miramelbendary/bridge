"use server";

import { redirect } from "next/navigation";

import type { SessionView } from "@/lib/api";
import { api } from "@/lib/auth";

import { attempt, type ActionResult, type FormState, text } from "./common";

type StepResponse = { result: Record<string, unknown>; view: SessionView };

const SAFE_ID = /^[a-z][a-z0-9_]{1,59}$/;

function sessionPath(sessionId: string): string {
  if (!/^[0-9a-f-]{36}$/i.test(sessionId)) throw new Error("bad session id");
  return `/api/v1/sessions/${sessionId}`;
}

export async function startSessionAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const slug = text(formData, "scenario_slug");
  const assignment = text(formData, "assignment_id") || undefined;
  const result = await attempt(() =>
    api<SessionView>("/api/v1/sessions", {
      method: "POST",
      body: {
        scenario_slug: slug,
        mode: text(formData, "mode") || "training",
        difficulty: text(formData, "difficulty") || "beginner",
        ...(assignment ? { assignment_id: assignment } : {}),
      },
    }),
  );
  if (!result.ok) return { error: result.error };
  redirect(`/sessions/${result.data.session_id}`);
}

export async function performActionStep(
  sessionId: string,
  actionId: string,
  justification: string,
  key: string,
): Promise<ActionResult<StepResponse>> {
  if (!SAFE_ID.test(actionId)) return { ok: false, error: "Unknown action." };
  return attempt(() =>
    api<StepResponse>(`${sessionPath(sessionId)}/actions`, {
      method: "POST",
      body: { action_id: actionId, justification },
      idempotencyKey: key,
    }),
  );
}

export async function sendMessageStep(
  sessionId: string,
  characterId: string,
  message: string,
  key: string,
): Promise<ActionResult<StepResponse>> {
  if (!SAFE_ID.test(characterId)) return { ok: false, error: "Unknown person." };
  return attempt(() =>
    api<StepResponse>(`${sessionPath(sessionId)}/messages`, {
      method: "POST",
      body: { character_id: characterId, text: message },
      idempotencyKey: key,
    }),
  );
}

export async function submitWorkStep(
  sessionId: string,
  submissionId: string,
  content: string,
  key: string,
): Promise<ActionResult<StepResponse>> {
  if (!SAFE_ID.test(submissionId)) return { ok: false, error: "Unknown deliverable." };
  return attempt(() =>
    api<StepResponse>(`${sessionPath(sessionId)}/submissions`, {
      method: "POST",
      body: { submission_id: submissionId, text: content },
      idempotencyKey: key,
    }),
  );
}

export async function hintStep(sessionId: string, key: string): Promise<ActionResult<StepResponse>> {
  return attempt(() =>
    api<StepResponse>(`${sessionPath(sessionId)}/hint`, { method: "POST", idempotencyKey: key }),
  );
}

export async function finishStep(sessionId: string, key: string): Promise<ActionResult<{ assessment_id: string }>> {
  const result = await attempt(() =>
    api<{ assessment_id: string; outcome_id: string }>(`${sessionPath(sessionId)}/finish`, {
      method: "POST",
      idempotencyKey: key,
    }),
  );
  if (result.ok) redirect(`/sessions/${sessionId}/report`);
  return result;
}

export async function abandonAction(formData: FormData): Promise<void> {
  const sessionId = text(formData, "session_id");
  await attempt(() => api(`${sessionPath(sessionId)}/abandon`, { method: "POST" }));
  redirect("/history");
}
