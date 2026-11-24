import type { Metadata } from "next";

import { updateProfileAction } from "@/app/actions/manage";
import { CompetencyChart } from "@/components/competency-chart";
import { StatefulForm } from "@/components/forms";
import { Badge, Card, EmptyState, Field, PageHeader, SectionTitle, inputClass } from "@/components/ui";
import type { CompetencyEntry, Recommendation, Specialization } from "@/lib/api";
import { api, getCurrentUser } from "@/lib/auth";
import { score, scoreTone, titleCase } from "@/lib/format";

export const metadata: Metadata = { title: "Competencies · BRIDGE" };

const CONFIDENCE = { low: "amber", medium: "blue", high: "teal" } as const;

export default async function ProfilePage() {
  const [user, profile, recommendations, specializations] = await Promise.all([
    getCurrentUser(),
    api<CompetencyEntry[]>("/api/v1/me/competencies"),
    api<Recommendation[]>("/api/v1/me/recommendations"),
    api<Specialization[]>("/api/v1/specializations"),
  ]);
  const observed = profile.filter((p) => p.average !== null);

  return (
    <>
      <PageHeader
        title="Competency profile"
        subtitle="Built from your assessed simulations. Confidence grows with the number of attempts."
      />
      {observed.length === 0 ? (
        <EmptyState title="No competencies measured yet">Complete a simulation to see your profile.</EmptyState>
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          <Card className="lg:col-span-3">
            <SectionTitle>Average score per competency</SectionTitle>
            <CompetencyChart
              data={observed.map((p) => ({ label: p.label, average: p.average ?? 0, attempts: p.attempts }))}
            />
          </Card>
          <Card className="lg:col-span-2">
            <SectionTitle>Details</SectionTitle>
            <ul className="divide-y divide-slate-200 dark:divide-slate-800">
              {profile.map((p) => (
                <li key={p.competency} className="py-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{p.label}</span>
                    <span className={`text-lg font-semibold ${scoreTone(p.average)}`}>{score(p.average)}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <Badge tone={CONFIDENCE[p.confidence]}>{titleCase(p.confidence)} confidence</Badge>
                    <span>
                      {p.attempts} assessed
                      {p.not_observed ? ` · ${p.not_observed} not observable` : ""}
                    </span>
                  </div>
                  {p.note ? <p className="mt-1 text-xs text-slate-500">{p.note}</p> : null}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <SectionTitle>Recommended learning activities</SectionTitle>
          <ul className="space-y-3">
            {recommendations.map((r) => (
              <li key={r.scenario_slug}>
                <Card>
                  <a href={`/scenarios/${r.scenario_slug}`} className="font-medium text-blue-800 hover:underline dark:text-blue-300">
                    {r.title}
                  </a>
                  <p className="text-sm text-slate-500">
                    {titleCase(r.mode)} · {titleCase(r.difficulty)}
                  </p>
                  <ul className="mt-2 list-disc pl-5 text-sm">
                    {r.reasons.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </Card>
              </li>
            ))}
          </ul>
        </section>
        <section>
          <SectionTitle>Your profile</SectionTitle>
          <Card>
            <StatefulForm action={updateProfileAction} submitLabel="Save profile">
              <Field label="Display name" htmlFor="display_name">
                <input id="display_name" name="display_name" className={inputClass} defaultValue={user.profile?.display_name} maxLength={120} />
              </Field>
              <Field label="Specialization" htmlFor="specialization_code">
                <select
                  id="specialization_code"
                  name="specialization_code"
                  className={inputClass}
                  defaultValue={user.profile?.specialization?.code ?? ""}
                >
                  <option value="">—</option>
                  {specializations.map((s) => (
                    <option key={s.code} value={s.code}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </Field>
            </StatefulForm>
          </Card>
        </section>
      </div>
    </>
  );
}
