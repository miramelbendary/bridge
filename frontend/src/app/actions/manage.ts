"use server";

import { refresh } from "next/cache";
import { redirect } from "next/navigation";

import { api } from "@/lib/auth";

import { attempt, type FormState, text } from "./common";

const UUID = /^[0-9a-f-]{36}$/i;

function id(formData: FormData, name: string): string {
  const value = text(formData, name);
  if (!UUID.test(value)) throw new Error(`invalid ${name}`);
  return value;
}

async function done(result: { ok: boolean; error?: string }, message: string): Promise<FormState> {
  if (!result.ok) return { error: result.error };
  refresh();
  return { message };
}

// ------------------------------------------------------------------ student profile
export async function updateProfileAction(_p: FormState, formData: FormData): Promise<FormState> {
  const body: Record<string, string> = {};
  const name = text(formData, "display_name");
  const spec = text(formData, "specialization_code");
  if (name) body.display_name = name;
  if (spec) body.specialization_code = spec;
  return done(await attempt(() => api("/api/v1/users/me/profile", { method: "PATCH", body })), "Profile updated.");
}

// ------------------------------------------------------------------ courses
export async function createCourseAction(_p: FormState, formData: FormData): Promise<FormState> {
  const result = await attempt(() =>
    api<{ id: string }>("/api/v1/teach/courses", {
      method: "POST",
      body: { name: text(formData, "name"), specialization_code: text(formData, "specialization_code") || null },
    }),
  );
  if (!result.ok) return { error: result.error };
  redirect(`/teach/courses/${result.data.id}`);
}

export async function addMemberAction(_p: FormState, formData: FormData): Promise<FormState> {
  const courseId = id(formData, "course_id");
  return done(
    await attempt(() =>
      api(`/api/v1/teach/courses/${courseId}/members`, { method: "POST", body: { email: text(formData, "email") } }),
    ),
    "Student added.",
  );
}

export async function removeMemberAction(formData: FormData): Promise<void> {
  const courseId = id(formData, "course_id");
  const studentId = id(formData, "student_id");
  await attempt(() => api(`/api/v1/teach/courses/${courseId}/members/${studentId}`, { method: "DELETE" }));
  refresh();
}

export async function addAssignmentAction(_p: FormState, formData: FormData): Promise<FormState> {
  const courseId = id(formData, "course_id");
  const due = text(formData, "due_at");
  return done(
    await attempt(() =>
      api(`/api/v1/teach/courses/${courseId}/assignments`, {
        method: "POST",
        body: {
          scenario_slug: text(formData, "scenario_slug"),
          mode: text(formData, "mode"),
          difficulty: text(formData, "difficulty"),
          due_at: due ? new Date(due).toISOString() : null,
        },
      }),
    ),
    "Assignment created.",
  );
}

export async function deleteAssignmentAction(formData: FormData): Promise<void> {
  const courseId = id(formData, "course_id");
  const assignmentId = id(formData, "assignment_id");
  await attempt(() => api(`/api/v1/teach/courses/${courseId}/assignments/${assignmentId}`, { method: "DELETE" }));
  refresh();
}

// ------------------------------------------------------------------ assessment review
export async function reviewAction(_p: FormState, formData: FormData): Promise<FormState> {
  const assessmentId = id(formData, "assessment_id");
  const criterion = text(formData, "criterion_id");
  const scoreRaw = text(formData, "new_score");
  const insufficient = formData.get("insufficient") === "on";
  const body = {
    criterion_id: criterion || null,
    new_score: criterion ? (insufficient || scoreRaw === "" ? null : Number(scoreRaw)) : null,
    justification: text(formData, "justification"),
  };
  if (body.new_score !== null && (Number.isNaN(body.new_score) || body.new_score < 0 || body.new_score > 100)) {
    return { error: "Score must be between 0 and 100." };
  }
  return done(
    await attempt(() => api(`/api/v1/teach/assessments/${assessmentId}/reviews`, { method: "POST", body })),
    criterion ? "Score corrected and recorded." : "Review recorded.",
  );
}

// ------------------------------------------------------------------ authoring
export async function validateScenarioAction(
  _p: FormState & { errors?: string[] },
  formData: FormData,
): Promise<FormState & { errors?: string[] }> {
  let definition: unknown;
  try {
    definition = JSON.parse(text(formData, "definition"));
  } catch {
    return { error: "The definition is not valid JSON." };
  }
  const intent = text(formData, "intent");
  if (intent === "save") {
    const result = await attempt(() =>
      api<{ version: number; created: boolean }>("/api/v1/teach/scenarios", {
        method: "POST",
        body: { definition, change_note: text(formData, "change_note") },
      }),
    );
    if (!result.ok) return { error: "Not saved — please fix these problems.", errors: result.error.split("\n") };
    refresh();
    return {
      message: result.data.created ? `Saved as version ${result.data.version}.` : "No changes — nothing to save.",
    };
  }
  const result = await attempt(() =>
    api<{ valid: boolean; errors: string[] }>("/api/v1/teach/scenarios/validate", { method: "POST", body: { definition } }),
  );
  if (!result.ok) return { error: result.error };
  return result.data.valid ? { message: "The scenario is valid." } : { error: "Validation failed.", errors: result.data.errors };
}

export async function saveRubricAction(_p: FormState & { errors?: string[] }, formData: FormData) {
  const slug = text(formData, "slug");
  let rubric: unknown;
  try {
    rubric = JSON.parse(text(formData, "rubric"));
  } catch {
    return { error: "Invalid rubric data." };
  }
  const result = await attempt(() =>
    api<{ version: number; created: boolean }>(`/api/v1/teach/scenarios/${encodeURIComponent(slug)}/rubric`, {
      method: "PUT",
      body: { rubric, change_note: text(formData, "change_note") },
    }),
  );
  if (!result.ok) return { error: "Not saved — please fix these problems.", errors: result.error.split("\n") };
  refresh();
  return { message: result.data.created ? `Rubric saved (scenario version ${result.data.version}).` : "No changes." };
}

export async function uploadResourceAction(_p: FormState, formData: FormData): Promise<FormState> {
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) return { error: "Choose a .txt or .md file." };
  if (file.size > 2_000_000) return { error: "File too large (max 2 MB)." };
  const content = await file.text();
  return done(
    await attempt(() =>
      api("/api/v1/teach/resources", {
        method: "POST",
        body: {
          title: text(formData, "title"),
          filename: file.name,
          content,
          visibility: text(formData, "visibility") || "students",
          specialization_code: text(formData, "specialization_code") || null,
        },
      }),
    ),
    "Resource uploaded and indexed.",
  );
}

export async function deleteResourceAction(formData: FormData): Promise<void> {
  const resourceId = id(formData, "resource_id");
  await attempt(() => api(`/api/v1/teach/resources/${resourceId}`, { method: "DELETE" }));
  refresh();
}

// ------------------------------------------------------------------ administration
export async function updateSettingsAction(_p: FormState, formData: FormData): Promise<FormState> {
  const changes: Record<string, unknown> = {
    ai_provider: text(formData, "ai_provider"),
    ai_max_messages_per_session: Number(text(formData, "ai_max_messages_per_session")),
    ai_daily_requests_per_user: Number(text(formData, "ai_daily_requests_per_user")),
    ai_session_budget_usd: Number(text(formData, "ai_session_budget_usd")),
    registration_open: formData.get("registration_open") === "on",
  };
  return done(await attempt(() => api("/api/v1/admin/settings", { method: "PATCH", body: { changes } })), "Settings saved.");
}

export async function setRoleAction(formData: FormData): Promise<void> {
  const userId = id(formData, "user_id");
  await attempt(() => api(`/api/v1/admin/users/${userId}/role`, { method: "PATCH", body: { role: text(formData, "role") } }));
  refresh();
}

export async function setActiveAction(formData: FormData): Promise<void> {
  const userId = id(formData, "user_id");
  await attempt(() =>
    api(`/api/v1/admin/users/${userId}/active`, { method: "PATCH", body: { is_active: text(formData, "is_active") === "true" } }),
  );
  refresh();
}

export async function scenarioStatusAction(formData: FormData): Promise<void> {
  const slug = text(formData, "slug");
  await attempt(() =>
    api(`/api/v1/admin/scenarios/${encodeURIComponent(slug)}/status`, { method: "POST", body: { status: text(formData, "status") } }),
  );
  refresh();
}

export async function createSpecializationAction(_p: FormState, formData: FormData): Promise<FormState> {
  return done(
    await attempt(() =>
      api("/api/v1/admin/specializations", {
        method: "POST",
        body: { code: text(formData, "code"), name: text(formData, "name"), description: text(formData, "description") },
      }),
    ),
    "Specialization created.",
  );
}

export async function toggleSpecializationAction(formData: FormData): Promise<void> {
  const specId = id(formData, "spec_id");
  await attempt(() =>
    api(`/api/v1/admin/specializations/${specId}`, { method: "PATCH", body: { is_active: text(formData, "is_active") === "true" } }),
  );
  refresh();
}
