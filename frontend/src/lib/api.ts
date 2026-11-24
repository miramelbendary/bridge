import "server-only";

/**
 * Server-side client for the BRIDGE FastAPI backend.
 * BRIDGE_API_URL is a server-only variable: the browser never talks to the backend directly.
 */
const API_URL = (process.env.BRIDGE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const TIMEOUT_MS = 60_000; // assessments with a real AI provider can take a while

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    public readonly code?: string,
  ) {
    super(`API ${status}: ${detail}`);
  }
}

function detailFrom(body: unknown, fallback: string): { message: string; code?: string } {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return { message: detail };
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      const d = detail as { message?: unknown; code?: unknown; errors?: unknown };
      if (Array.isArray(d.errors)) return { message: d.errors.join("\n"), code: String(d.code ?? "") };
      if (typeof d.message === "string") return { message: d.message, code: typeof d.code === "string" ? d.code : undefined };
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return {
        message: detail
          .map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d)))
          .join("; "),
      };
    }
  }
  return { message: fallback };
}

export type FetchOptions = {
  token?: string;
  method?: string;
  body?: unknown;
  idempotencyKey?: string;
  raw?: boolean;
};

export async function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { token, method = "GET", body, idempotencyKey, raw } = opts;
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        Accept: raw ? "*/*" : "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    throw new ApiError(503, "The BRIDGE service is unreachable. Please try again shortly.");
  }
  if (raw) {
    if (!response.ok) throw new ApiError(response.status, response.statusText);
    return response as unknown as T;
  }
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const { message, code } = detailFrom(data, response.statusText || "Request failed");
    throw new ApiError(response.status, message, code);
  }
  return data as T;
}

// ------------------------------------------------------------------ shared types
export type Role = "student" | "professor" | "admin";

export type Specialization = { id: string; code: string; name: string; description: string };

export type CurrentUser = {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  permissions: string[];
  profile: { display_name: string; specialization: Specialization | null } | null;
};

export type TokenResponse = { access_token: string; token_type: "bearer"; expires_in: number };

export type ScenarioSummary = {
  id: string;
  slug: string;
  status: string;
  version: number;
  specialization: { code: string; name: string };
  title: string;
  summary: string;
  estimated_minutes: number;
  difficulties: string[];
  competencies: string[];
};

export type ScenarioDetail = ScenarioSummary & {
  learning_objectives: string[];
  context: { organization: string; student_role: string; briefing: string; fictional_notice: string };
  difficulty_settings: Record<string, { time_limit_minutes: number; hints_available: boolean; description: string }>;
  characters: { name: string; role: string; organization: string; kind: string }[];
  rubric: { name: string; weight: number; competency: string }[];
  review_status: string;
};

export type ConversationEntry = {
  role: "student" | "character";
  text: string;
  minute: number;
  seq: number;
  label?: string;
};

export type SessionView = {
  session_id: string;
  scenario_slug: string | null;
  status: string;
  read_only?: boolean;
  assessment_id: string | null;
  title: string;
  summary: string;
  context: { organization: string; student_role: string; briefing: string; fictional_notice: string };
  learning_objectives: string[];
  mode: "training" | "assessment";
  difficulty: string;
  clock: number;
  time_limit: number;
  time_up: boolean;
  finished: boolean;
  variables: { id: string; label: string; value: number; unit: string; min: number | null; max: number | null; description: string }[];
  characters: { id: string; name: string; role: string; kind: string; organization: string; mood: string; language: string }[];
  inbox: { id: string; sender: string; subject: string; body: string; minute: number }[];
  conversations: Record<string, ConversationEntry[]>;
  documents: { id: string; title: string; kind: string; body: string; direction: "ltr" | "rtl" }[];
  tasks: { id: string; title: string; description: string; required: boolean; status: "open" | "done" }[];
  actions: {
    id: string;
    label: string;
    description: string;
    category: string;
    requires_justification: boolean;
    duration_minutes: number;
    via_character: string | null;
  }[];
  submissions: {
    id: string;
    title: string;
    prompt: string;
    min_words: number;
    direction: "ltr" | "rtl";
    language: string;
    template: string;
    current: { text: string; words: number; revision: number; minute: number } | null;
  }[];
  log: { minute: number; kind: string; text: string }[];
  feedback: { minute: number; text: string }[];
  hints_available: boolean;
  fictional_notice: string;
};

export type SessionListItem = {
  id: string;
  scenario_slug: string | null;
  scenario_title: string;
  scenario_version: number;
  specialization: string | null;
  mode: string;
  difficulty: string;
  status: string;
  outcome: string | null;
  started_at: string;
  completed_at: string | null;
  overall_score: number | null;
  assessment_id: string | null;
  assessment_status: string | null;
};

export type CriterionResult = {
  criterion_id: string;
  name: string;
  description: string;
  competency: string;
  weight: number;
  insufficient_evidence: boolean;
  qualitative_score: number | null;
  objective_score: number | null;
  original_score: number | null;
  final_score: number | null;
  level_label: string;
  explanation: string;
  evidence: { ref: string; summary: string; excerpt: string }[];
  weaknesses: string[];
  improvements: string[];
  uncertainty: string;
};

export type AssessmentData = {
  id: string;
  session_id: string;
  student_id: string;
  status: string;
  provider: string;
  model: string;
  is_mock: boolean;
  original_overall: number | null;
  final_overall: number | null;
  flags: string[];
  mode: string;
  difficulty: string;
  created_at: string;
  criteria: CriterionResult[];
  report: {
    scenario_title: string;
    outcome: { id: string; title: string; description: string };
    overall_feedback: string;
    strengths: string[];
    areas_for_improvement: { criterion: string; competency: string; score: number; weaknesses: string[]; improvements: string[] }[];
    not_assessed: string[];
    assessed_weight_percent: number;
    key_decisions: {
      minute: number;
      label: string;
      justification: string;
      consequence: string;
      effects: { label: string; before: number; after: number; unit: string }[];
      via: string;
    }[];
    alternative_approaches: string[];
    concepts_to_revise: { concept: string; criterion: string; resources: { title: string; heading: string; excerpt: string }[] }[];
    final_variables: { label: string; value: number; unit: string }[];
    disclaimer: string;
    review_status: string;
  };
  reviews: { criterion_id: string | null; previous_score: number | null; new_score: number | null; justification: string; created_at: string }[];
};

export type CompetencyEntry = {
  competency: string;
  label: string;
  average: number | null;
  latest: number | null;
  attempts: number;
  not_observed: number;
  trend: { score: number; at: string | null }[];
  confidence: "low" | "medium" | "high";
  note: string;
};

export type Recommendation = {
  scenario_slug: string;
  title: string;
  specialization: string;
  difficulty: string;
  mode: string;
  reasons: string[];
};

export type Assignment = {
  id: string;
  course: string;
  scenario_slug: string;
  scenario_title: string;
  mode: string;
  difficulty: string;
  due_at: string | null;
  completed: boolean;
};
