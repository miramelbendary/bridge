import Link from "next/link";

import { Card, EmptyState, PageHeader, SectionTitle } from "@/components/ui";
import type { CompetencyEntry, SessionListItem } from "@/lib/api";
import { api, requireRole } from "@/lib/auth";
import { dateTime, score, scoreTone, titleCase } from "@/lib/format";

type StudentData = {
  student: { id: string; display_name: string; email: string };
  sessions: SessionListItem[];
  competencies: CompetencyEntry[];
};

export default async function StudentPage(props: PageProps<"/teach/students/[id]">) {
  await requireRole("professor", "admin");
  const { id } = await props.params;
  const data = await api<StudentData>(`/api/v1/teach/students/${encodeURIComponent(id)}/sessions`);
  return (
    <>
      <PageHeader title={data.student.display_name} subtitle={data.student.email} />
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <SectionTitle>Attempts</SectionTitle>
          {data.sessions.length === 0 ? (
            <EmptyState title="No attempts yet" />
          ) : (
            <ul className="space-y-2">
              {data.sessions.map((s) => (
                <li key={s.id}>
                  <Card className="!p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm">
                        <p className="font-medium">{s.scenario_title}</p>
                        <p className="text-xs text-slate-500">
                          {titleCase(s.mode)} · {titleCase(s.difficulty)} · {dateTime(s.started_at)} · {s.outcome ?? titleCase(s.status)}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`text-lg font-semibold ${scoreTone(s.overall_score)}`}>{score(s.overall_score)}</span>
                        {s.assessment_id ? (
                          <Link href={`/teach/assessments/${s.assessment_id}`} className="text-sm text-blue-700 hover:underline dark:text-blue-300">
                            Review
                          </Link>
                        ) : null}
                        <Link href={`/sessions/${s.id}`} className="text-sm text-slate-600 hover:underline dark:text-slate-300">
                          Workplace
                        </Link>
                      </div>
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section>
          <SectionTitle>Competencies</SectionTitle>
          <Card>
            {data.competencies.length === 0 ? (
              <p className="text-sm text-slate-500">Not measured yet.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {data.competencies.map((c) => (
                  <li key={c.competency} className="flex justify-between gap-2">
                    <span>{c.label}</span>
                    <span className={`font-semibold ${scoreTone(c.average)}`}>
                      {score(c.average)} <span className="text-xs font-normal text-slate-500">({c.attempts})</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </section>
      </div>
    </>
  );
}
