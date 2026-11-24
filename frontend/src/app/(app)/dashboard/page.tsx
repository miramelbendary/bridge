import type { Metadata } from "next";
import Link from "next/link";

import { updateProfileAction } from "@/app/actions/manage";
import { StatefulForm } from "@/components/forms";
import { Badge, ButtonLink, Card, EmptyState, Field, inputClass, PageHeader, SectionTitle } from "@/components/ui";
import type { Assignment, Recommendation, SessionListItem, Specialization } from "@/lib/api";
import { api, getCurrentUser } from "@/lib/auth";
import { dateTime, score, scoreTone, titleCase } from "@/lib/format";

export const metadata: Metadata = { title: "Dashboard · BRIDGE" };

export default async function DashboardPage() {
  const [user, specializations, assignments, recommendations, sessions] = await Promise.all([
    getCurrentUser(),
    api<Specialization[]>("/api/v1/specializations"),
    api<Assignment[]>("/api/v1/me/assignments"),
    api<Recommendation[]>("/api/v1/me/recommendations"),
    api<SessionListItem[]>("/api/v1/sessions"),
  ]);
  const name = user.profile?.display_name ?? user.email;
  const active = sessions.filter((s) => s.status === "active");
  const recent = sessions.filter((s) => s.status === "completed").slice(0, 4);
  const spec = user.profile?.specialization;

  return (
    <>
      <PageHeader
        title={`Welcome, ${name}`}
        subtitle={spec ? `Specialization: ${spec.name}` : "Choose your specialization to get tailored recommendations."}
        actions={<ButtonLink href="/scenarios">Browse scenarios</ButtonLink>}
      />

      {!spec ? (
        <Card className="mb-6">
          <SectionTitle>Choose your specialization</SectionTitle>
          <StatefulForm action={updateProfileAction} submitLabel="Save" className="max-w-md">
            <Field label="Specialization" htmlFor="specialization_code">
              <select id="specialization_code" name="specialization_code" className={inputClass} required defaultValue="">
                <option value="" disabled>
                  Select…
                </option>
                {specializations.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>
          </StatefulForm>
        </Card>
      ) : null}

      {active.length ? (
        <Card className="mb-6 border-blue-200 dark:border-blue-900">
          <SectionTitle>Continue where you left off</SectionTitle>
          <ul className="space-y-2">
            {active.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm">
                  <span className="font-medium">{s.scenario_title}</span>{" "}
                  <span className="text-slate-500">· {titleCase(s.mode)} · {titleCase(s.difficulty)}</span>
                </span>
                <ButtonLink href={`/sessions/${s.id}`} variant="secondary">
                  Resume
                </ButtonLink>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="assignments">
          <SectionTitle id="assignments">Assigned by your professors</SectionTitle>
          {assignments.length === 0 ? (
            <EmptyState title="No assignments">Your professors have not assigned any simulations yet.</EmptyState>
          ) : (
            <ul className="space-y-3">
              {assignments.map((a) => (
                <li key={a.id}>
                  <Card>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">{a.scenario_title}</p>
                        <p className="text-sm text-slate-500">
                          {a.course} · {titleCase(a.mode)} · {titleCase(a.difficulty)}
                          {a.due_at ? ` · due ${dateTime(a.due_at)}` : ""}
                        </p>
                      </div>
                      {a.completed ? (
                        <Badge tone="teal">Completed</Badge>
                      ) : (
                        <ButtonLink href={`/scenarios/${a.scenario_slug}?assignment=${a.id}`} variant="secondary">
                          Start
                        </ButtonLink>
                      )}
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="recommended">
          <SectionTitle id="recommended">Recommended next</SectionTitle>
          {recommendations.length === 0 ? (
            <EmptyState title="No recommendations yet" />
          ) : (
            <ul className="space-y-3">
              {recommendations.map((r) => (
                <li key={r.scenario_slug}>
                  <Card>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <Link href={`/scenarios/${r.scenario_slug}`} className="font-medium text-blue-800 hover:underline dark:text-blue-300">
                          {r.title}
                        </Link>
                        <p className="text-sm text-slate-500">
                          {r.specialization} · suggested: {titleCase(r.mode)}, {titleCase(r.difficulty)}
                        </p>
                      </div>
                    </div>
                    <p className="mt-2 text-xs font-medium uppercase tracking-wide text-slate-500">Why</p>
                    <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700 dark:text-slate-300">
                      {r.reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section aria-labelledby="recent" className="mt-8">
        <SectionTitle id="recent">Recent results</SectionTitle>
        {recent.length === 0 ? (
          <EmptyState title="No completed simulations yet">
            Finish a simulation to receive your first personalised report.
          </EmptyState>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {recent.map((s) => (
              <Link key={s.id} href={`/sessions/${s.id}/report`} className="block">
                <Card className="h-full hover:border-blue-300 dark:hover:border-blue-800">
                  <p className={`text-3xl font-semibold ${scoreTone(s.overall_score)}`}>{score(s.overall_score)}</p>
                  <p className="mt-1 text-sm font-medium">{s.scenario_title}</p>
                  <p className="text-xs text-slate-500">{s.outcome}</p>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
