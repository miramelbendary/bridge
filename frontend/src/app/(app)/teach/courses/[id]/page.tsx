import Link from "next/link";

import {
  addAssignmentAction,
  addMemberAction,
  deleteAssignmentAction,
  removeMemberAction,
} from "@/app/actions/manage";
import { StatefulForm } from "@/components/forms";
import { Card, EmptyState, Field, Meter, PageHeader, SectionTitle, inputClass } from "@/components/ui";
import type { ScenarioSummary } from "@/lib/api";
import { api, requireRole } from "@/lib/auth";
import { dateTime, score, scoreTone, titleCase } from "@/lib/format";

type CourseDetail = {
  id: string;
  name: string;
  students: { id: string; email: string; display_name: string }[];
  assignments: { id: string; scenario_slug: string; scenario_title: string; mode: string; difficulty: string; due_at: string | null }[];
};
type Progress = {
  course: string;
  students: { id: string; display_name: string; email: string; attempts: number; average: number | null; latest: number | null; needs_review: number }[];
  competencies: { competency: string; label: string; average: number; observations: number }[];
};

export default async function CoursePage(props: PageProps<"/teach/courses/[id]">) {
  await requireRole("professor", "admin");
  const { id } = await props.params;
  const [course, progress, scenarios] = await Promise.all([
    api<CourseDetail>(`/api/v1/teach/courses/${encodeURIComponent(id)}`),
    api<Progress>(`/api/v1/teach/courses/${encodeURIComponent(id)}/progress`),
    api<ScenarioSummary[]>("/api/v1/scenarios"),
  ]);
  const published = scenarios.filter((s) => s.status === "published");
  const byStudent = Object.fromEntries(progress.students.map((s) => [s.id, s]));

  return (
    <>
      <PageHeader
        title={course.name}
        subtitle={`${course.students.length} students · ${course.assignments.length} assignments`}
        actions={
          <a
            href={`/api/export/${course.id}`}
            className="inline-flex items-center rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Export results (CSV)
          </a>
        }
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2 space-y-6">
          <div>
            <SectionTitle>Students</SectionTitle>
            {course.students.length === 0 ? (
              <EmptyState title="No students yet">Add students by the email they registered with.</EmptyState>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-500 dark:bg-slate-900">
                    <tr>
                      <th className="px-3 py-2">Student</th>
                      <th className="px-3 py-2 text-right">Attempts</th>
                      <th className="px-3 py-2 text-right">Average</th>
                      <th className="px-3 py-2 text-right">Latest</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                    {course.students.map((s) => {
                      const p = byStudent[s.id];
                      return (
                        <tr key={s.id}>
                          <td className="px-3 py-2">
                            <Link href={`/teach/students/${s.id}`} className="font-medium text-blue-800 hover:underline dark:text-blue-300">
                              {s.display_name}
                            </Link>
                            <span className="block text-xs text-slate-500">{s.email}</span>
                          </td>
                          <td className="px-3 py-2 text-right">{p?.attempts ?? 0}</td>
                          <td className={`px-3 py-2 text-right font-semibold ${scoreTone(p?.average)}`}>{score(p?.average)}</td>
                          <td className="px-3 py-2 text-right">{score(p?.latest)}</td>
                          <td className="px-3 py-2 text-right">
                            <form action={removeMemberAction}>
                              <input type="hidden" name="course_id" value={course.id} />
                              <input type="hidden" name="student_id" value={s.id} />
                              <button type="submit" className="text-xs text-red-700 hover:underline dark:text-red-400">
                                Remove
                              </button>
                            </form>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div>
            <SectionTitle>Common weaknesses</SectionTitle>
            {progress.competencies.length === 0 ? (
              <p className="text-sm text-slate-500">No assessed attempts yet.</p>
            ) : (
              <Card>
                <ul className="space-y-3">
                  {progress.competencies.map((c) => (
                    <li key={c.competency}>
                      <div className="flex justify-between text-sm">
                        <span>{c.label}</span>
                        <span className={`font-semibold ${scoreTone(c.average)}`}>
                          {score(c.average)} <span className="text-xs font-normal text-slate-500">({c.observations} obs.)</span>
                        </span>
                      </div>
                      <Meter value={c.average} label={c.label} />
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs text-slate-500">Lowest averages first. Few observations mean low confidence.</p>
              </Card>
            )}
          </div>

          <div>
            <SectionTitle>Assignments</SectionTitle>
            {course.assignments.length === 0 ? (
              <p className="text-sm text-slate-500">No assignments yet.</p>
            ) : (
              <ul className="space-y-2">
                {course.assignments.map((a) => (
                  <li key={a.id}>
                    <Card className="!p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm">
                          <span className="font-medium">{a.scenario_title}</span> · {titleCase(a.mode)} · {titleCase(a.difficulty)}
                          {a.due_at ? ` · due ${dateTime(a.due_at)}` : ""}
                        </span>
                        <form action={deleteAssignmentAction}>
                          <input type="hidden" name="course_id" value={course.id} />
                          <input type="hidden" name="assignment_id" value={a.id} />
                          <button type="submit" className="text-xs text-red-700 hover:underline dark:text-red-400">
                            Delete
                          </button>
                        </form>
                      </div>
                    </Card>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <aside className="space-y-6">
          <Card>
            <p className="mb-2 text-sm font-semibold">Add a student</p>
            <StatefulForm action={addMemberAction} submitLabel="Add">
              <input type="hidden" name="course_id" value={course.id} />
              <Field label="Student email" htmlFor="email">
                <input id="email" name="email" type="email" required className={inputClass} />
              </Field>
            </StatefulForm>
          </Card>
          <Card>
            <p className="mb-2 text-sm font-semibold">Assign a simulation</p>
            <StatefulForm action={addAssignmentAction} submitLabel="Assign">
              <input type="hidden" name="course_id" value={course.id} />
              <Field label="Scenario" htmlFor="scenario_slug">
                <select id="scenario_slug" name="scenario_slug" className={inputClass} required>
                  {published.map((s) => (
                    <option key={s.slug} value={s.slug}>
                      {s.title} ({s.specialization.name})
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Mode" htmlFor="mode">
                <select id="mode" name="mode" className={inputClass} defaultValue="assessment">
                  <option value="assessment">Assessment</option>
                  <option value="training">Training</option>
                </select>
              </Field>
              <Field label="Difficulty" htmlFor="difficulty">
                <select id="difficulty" name="difficulty" className={inputClass} defaultValue="beginner">
                  {["beginner", "intermediate", "advanced", "professional"].map((d) => (
                    <option key={d} value={d}>
                      {titleCase(d)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Due (optional)" htmlFor="due_at">
                <input id="due_at" name="due_at" type="datetime-local" className={inputClass} />
              </Field>
            </StatefulForm>
          </Card>
        </aside>
      </div>
    </>
  );
}
