import { startSessionAction } from "@/app/actions/sim";
import { StatefulForm } from "@/components/forms";
import { Alert, Badge, Card, Field, PageHeader, SectionTitle, inputClass } from "@/components/ui";
import type { Assignment, ScenarioDetail } from "@/lib/api";
import { api } from "@/lib/auth";
import { titleCase } from "@/lib/format";

export default async function ScenarioIntroPage(props: PageProps<"/scenarios/[slug]">) {
  const { slug } = await props.params;
  const search = (await props.searchParams) as { assignment?: string };
  const [s, assignments] = await Promise.all([
    api<ScenarioDetail>(`/api/v1/scenarios/${encodeURIComponent(slug)}`),
    api<Assignment[]>("/api/v1/me/assignments"),
  ]);
  const assignment = assignments.find((a) => a.id === search.assignment && a.scenario_slug === slug);

  return (
    <>
      <PageHeader title={s.title} subtitle={`${s.specialization.name} · about ${s.estimated_minutes} minutes`} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <SectionTitle>Your role</SectionTitle>
            <p className="text-sm">
              <span className="font-medium">{s.context.student_role}</span> at {s.context.organization}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{s.context.briefing}</p>
            <p className="mt-3 text-xs text-slate-500">{s.context.fictional_notice}</p>
          </Card>
          <Card>
            <SectionTitle>Learning objectives</SectionTitle>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {s.learning_objectives.map((o) => (
                <li key={o}>{o}</li>
              ))}
            </ul>
          </Card>
          <Card>
            <SectionTitle>People you will work with</SectionTitle>
            <ul className="grid gap-2 sm:grid-cols-2">
              {s.characters.map((c) => (
                <li key={c.name} className="text-sm">
                  <span className="font-medium">{c.name}</span>
                  <span className="block text-slate-500">
                    {c.role}, {c.organization}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
          <Card>
            <SectionTitle>How you will be assessed</SectionTitle>
            <ul className="space-y-1 text-sm">
              {s.rubric.map((r) => (
                <li key={r.name} className="flex justify-between gap-4">
                  <span>{r.name}</span>
                  <span className="text-slate-500">{r.weight}%</span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-slate-500">{s.review_status}</p>
          </Card>
        </div>

        <Card className="h-fit">
          <SectionTitle>Start the simulation</SectionTitle>
          {assignment ? (
            <Alert tone="info">
              Assigned in <strong>{assignment.course}</strong>: {titleCase(assignment.mode)} mode,{" "}
              {titleCase(assignment.difficulty)} difficulty.
            </Alert>
          ) : null}
          <StatefulForm action={startSessionAction} submitLabel="Enter the workplace" className="mt-3">
            <input type="hidden" name="scenario_slug" value={s.slug} />
            {assignment ? (
              <input type="hidden" name="assignment_id" value={assignment.id} />
            ) : (
              <>
                <Field label="Mode" htmlFor="mode" hint="Training: hints and feedback during the task. Assessment: feedback only at the end.">
                  <select id="mode" name="mode" className={inputClass} defaultValue="training">
                    <option value="training">Training</option>
                    <option value="assessment">Assessment</option>
                  </select>
                </Field>
                <Field label="Difficulty" htmlFor="difficulty">
                  <select id="difficulty" name="difficulty" className={inputClass} defaultValue={s.difficulties[0]}>
                    {s.difficulties.map((d) => (
                      <option key={d} value={d}>
                        {titleCase(d)} — {s.difficulty_settings[d]?.time_limit_minutes} simulated min
                        {s.difficulty_settings[d]?.hints_available ? "" : ", no hints"}
                      </option>
                    ))}
                  </select>
                </Field>
              </>
            )}
          </StatefulForm>
          <div className="mt-4 flex flex-wrap gap-1">
            {s.competencies.map((c) => (
              <Badge key={c}>{titleCase(c)}</Badge>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
