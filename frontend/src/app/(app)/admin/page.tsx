import type { Metadata } from "next";

import {
  createSpecializationAction,
  scenarioStatusAction,
  setActiveAction,
  setRoleAction,
  toggleSpecializationAction,
  updateSettingsAction,
} from "@/app/actions/manage";
import { StatefulForm } from "@/components/forms";
import { Badge, Card, Field, PageHeader, SectionTitle, inputClass } from "@/components/ui";
import type { ScenarioSummary } from "@/lib/api";
import { api, requireRole } from "@/lib/auth";
import { dateTime, titleCase } from "@/lib/format";

export const metadata: Metadata = { title: "Administration · BRIDGE" };

type AdminUser = { id: string; email: string; role: string; is_active: boolean; created_at: string; profile: { display_name: string } | null };
type Settings = {
  values: {
    ai_provider: string;
    ai_max_messages_per_session: number;
    ai_daily_requests_per_user: number;
    ai_session_budget_usd: number;
    registration_open: boolean;
  };
  anthropic_configured: boolean;
  ai_model: string;
};
type Usage = {
  days: number;
  sessions_started: number;
  sessions_completed: number;
  completion_rate: number | null;
  breakdown: {
    provider: string;
    purpose: string;
    calls: number;
    input_tokens: number;
    output_tokens: number;
    estimated_cost_usd: number;
    avg_latency_ms: number;
    failures: number;
    fallbacks: number;
  }[];
  recent_errors: { at: string; provider: string; purpose: string; error: string }[];
};
type AdminSpec = { id: string; code: string; name: string; description: string; is_active: boolean };
type Audit = { id: string; occurred_at: string; action: string; outcome: string; actor_user_id: string | null; target_id: string | null; details: Record<string, unknown> };

const smallSelect = "rounded-md border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-950";

export default async function AdminPage() {
  const me = await requireRole("admin");
  const [users, settings, usage, specs, scenarios, audit] = await Promise.all([
    api<AdminUser[]>("/api/v1/admin/users?limit=200"),
    api<Settings>("/api/v1/admin/settings"),
    api<Usage>("/api/v1/admin/usage?days=7"),
    api<AdminSpec[]>("/api/v1/admin/specializations"),
    api<ScenarioSummary[]>("/api/v1/admin/scenarios"),
    api<Audit[]>("/api/v1/admin/audit-logs?limit=40"),
  ]);

  return (
    <>
      <PageHeader title="Administration" subtitle="Users, AI configuration, usage, content publication and security logs." />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <SectionTitle>Last 7 days</SectionTitle>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-slate-500">Sessions started</dt>
              <dd className="text-2xl font-semibold">{usage.sessions_started}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Completion rate</dt>
              <dd className="text-2xl font-semibold">{usage.completion_rate === null ? "—" : `${usage.completion_rate}%`}</dd>
            </div>
          </dl>
          <div className="mt-4 overflow-x-auto [&_td]:px-1.5 [&_th]:px-1.5">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-500">
                <tr>
                  <th className="py-1">Provider / purpose</th>
                  <th className="py-1 text-right">Calls</th>
                  <th className="py-1 text-right">Cost $</th>
                  <th className="py-1 text-right">Latency</th>
                  <th className="py-1 text-right">Fails</th>
                </tr>
              </thead>
              <tbody>
                {usage.breakdown.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-2 text-slate-500">
                      No AI calls yet.
                    </td>
                  </tr>
                ) : null}
                {usage.breakdown.map((b) => (
                  <tr key={b.provider + b.purpose} className="border-t border-slate-200 dark:border-slate-800">
                    <td className="py-1">
                      {b.provider} / {b.purpose}
                    </td>
                    <td className="py-1 text-right">{b.calls}</td>
                    <td className="py-1 text-right">{b.estimated_cost_usd.toFixed(3)}</td>
                    <td className="py-1 text-right">{b.avg_latency_ms} ms</td>
                    <td className="py-1 text-right">
                      {b.failures}
                      {b.fallbacks ? ` (${b.fallbacks} fb)` : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {usage.recent_errors.length ? (
            <details className="mt-3 text-xs">
              <summary className="cursor-pointer font-medium">Recent AI errors ({usage.recent_errors.length})</summary>
              <ul className="mt-1 space-y-1">
                {usage.recent_errors.map((e, i) => (
                  <li key={i}>
                    {dateTime(e.at)} · {e.provider}/{e.purpose}: {e.error}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </Card>

        <Card className="lg:col-span-2">
          <SectionTitle>AI and platform settings</SectionTitle>
          <StatefulForm action={updateSettingsAction} submitLabel="Save settings">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field
                label="AI provider"
                htmlFor="ai_provider"
                hint={settings.anthropic_configured ? `Claude API available (${settings.ai_model}).` : "Set ANTHROPIC_API_KEY on the server to enable the Claude API."}
              >
                <select id="ai_provider" name="ai_provider" className={inputClass} defaultValue={settings.values.ai_provider}>
                  <option value="mock">Mock (offline, free, deterministic)</option>
                  <option value="anthropic" disabled={!settings.anthropic_configured}>
                    Anthropic Claude API
                  </option>
                </select>
              </Field>
              <Field label="Max AI messages per session" htmlFor="ai_max_messages_per_session">
                <input id="ai_max_messages_per_session" name="ai_max_messages_per_session" type="number" min={1} className={inputClass} defaultValue={settings.values.ai_max_messages_per_session} />
              </Field>
              <Field label="Daily AI requests per user" htmlFor="ai_daily_requests_per_user">
                <input id="ai_daily_requests_per_user" name="ai_daily_requests_per_user" type="number" min={1} className={inputClass} defaultValue={settings.values.ai_daily_requests_per_user} />
              </Field>
              <Field label="Cost budget per session (USD)" htmlFor="ai_session_budget_usd">
                <input id="ai_session_budget_usd" name="ai_session_budget_usd" type="number" min={0.01} step={0.01} className={inputClass} defaultValue={settings.values.ai_session_budget_usd} />
              </Field>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" name="registration_open" defaultChecked={settings.values.registration_open} /> Allow new student registrations
            </label>
          </StatefulForm>
        </Card>
      </div>

      <section className="mt-8">
        <SectionTitle>Users</SectionTitle>
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500 dark:bg-slate-900">
              <tr>
                <th className="px-3 py-2">User</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Joined</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="px-3 py-2">
                    {u.profile?.display_name ?? "—"}
                    <span className="block text-xs text-slate-500">{u.email}</span>
                  </td>
                  <td className="px-3 py-2">
                    <form action={setRoleAction} className="flex items-center gap-2">
                      <input type="hidden" name="user_id" value={u.id} />
                      <select name="role" defaultValue={u.role} className={smallSelect} aria-label={`Role for ${u.email}`} disabled={u.id === me.id}>
                        <option value="student">Student</option>
                        <option value="professor">Professor</option>
                        <option value="admin">Admin</option>
                      </select>
                      {u.id !== me.id ? (
                        <button type="submit" className="text-xs text-blue-700 hover:underline dark:text-blue-300">
                          Apply
                        </button>
                      ) : (
                        <span className="text-xs text-slate-500">(you)</span>
                      )}
                    </form>
                  </td>
                  <td className="px-3 py-2">
                    <form action={setActiveAction} className="flex items-center gap-2">
                      <input type="hidden" name="user_id" value={u.id} />
                      <input type="hidden" name="is_active" value={u.is_active ? "false" : "true"} />
                      <Badge tone={u.is_active ? "teal" : "red"}>{u.is_active ? "Active" : "Deactivated"}</Badge>
                      {u.id !== me.id ? (
                        <button type="submit" className="text-xs text-blue-700 hover:underline dark:text-blue-300">
                          {u.is_active ? "Deactivate" : "Reactivate"}
                        </button>
                      ) : null}
                    </form>
                  </td>
                  <td className="px-3 py-2 text-xs">{dateTime(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <SectionTitle>Scenario publication</SectionTitle>
          <ul className="space-y-2">
            {scenarios.map((s) => (
              <li key={s.slug}>
                <Card className="!p-3">
                  <form action={scenarioStatusAction} className="flex flex-wrap items-center justify-between gap-2">
                    <input type="hidden" name="slug" value={s.slug} />
                    <span className="text-sm">
                      <span className="font-medium">{s.title}</span>
                      <span className="block text-xs text-slate-500">
                        {s.specialization.name} · v{s.version}
                      </span>
                    </span>
                    <span className="flex items-center gap-2">
                      <select name="status" defaultValue={s.status} className={smallSelect} aria-label={`Status of ${s.title}`}>
                        <option value="draft">Draft</option>
                        <option value="published">Published</option>
                        <option value="archived">Archived</option>
                      </select>
                      <button type="submit" className="text-xs text-blue-700 hover:underline dark:text-blue-300">
                        Apply
                      </button>
                    </span>
                  </form>
                </Card>
              </li>
            ))}
          </ul>
        </section>
        <section>
          <SectionTitle>Specializations</SectionTitle>
          <ul className="mb-4 space-y-2">
            {specs.map((s) => (
              <li key={s.id}>
                <Card className="!p-3">
                  <form action={toggleSpecializationAction} className="flex items-center justify-between gap-2">
                    <input type="hidden" name="spec_id" value={s.id} />
                    <input type="hidden" name="is_active" value={s.is_active ? "false" : "true"} />
                    <span className="text-sm">
                      {s.name} <span className="text-xs text-slate-500">({s.code})</span>
                    </span>
                    <span className="flex items-center gap-2">
                      <Badge tone={s.is_active ? "teal" : "slate"}>{s.is_active ? "Active" : "Inactive"}</Badge>
                      <button type="submit" className="text-xs text-blue-700 hover:underline dark:text-blue-300">
                        {s.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </span>
                  </form>
                </Card>
              </li>
            ))}
          </ul>
          <Card>
            <p className="mb-2 text-sm font-semibold">Add a specialization</p>
            <StatefulForm action={createSpecializationAction} submitLabel="Create">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Code" htmlFor="code" hint="lowercase_with_underscores">
                  <input id="code" name="code" required pattern="[a-z][a-z0-9_]{1,49}" className={inputClass} />
                </Field>
                <Field label="Name" htmlFor="spec_name">
                  <input id="spec_name" name="name" required className={inputClass} />
                </Field>
              </div>
              <Field label="Description" htmlFor="description">
                <input id="description" name="description" className={inputClass} />
              </Field>
            </StatefulForm>
          </Card>
        </section>
      </div>

      <section className="mt-8">
        <SectionTitle>Security and audit log (latest 40)</SectionTitle>
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 uppercase text-slate-500 dark:bg-slate-900">
              <tr>
                <th className="px-3 py-2">When</th>
                <th className="px-3 py-2">Action</th>
                <th className="px-3 py-2">Outcome</th>
                <th className="px-3 py-2">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {audit.map((e) => (
                <tr key={e.id}>
                  <td className="px-3 py-1.5 whitespace-nowrap">{dateTime(e.occurred_at)}</td>
                  <td className="px-3 py-1.5">{e.action}</td>
                  <td className="px-3 py-1.5">
                    <Badge tone={e.outcome === "success" ? "teal" : e.outcome === "denied" ? "red" : "amber"}>{titleCase(e.outcome)}</Badge>
                  </td>
                  <td className="px-3 py-1.5 font-mono">{JSON.stringify(e.details)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
