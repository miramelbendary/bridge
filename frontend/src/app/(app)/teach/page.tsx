import type { Metadata } from "next";
import Link from "next/link";

import { createCourseAction } from "@/app/actions/manage";
import { StatefulForm } from "@/components/forms";
import { Badge, ButtonLink, Card, EmptyState, Field, PageHeader, SectionTitle, inputClass } from "@/components/ui";
import type { Specialization } from "@/lib/api";
import { api, requireRole } from "@/lib/auth";
import { dateTime, score, scoreTone, titleCase } from "@/lib/format";

export const metadata: Metadata = { title: "Teaching · BRIDGE" };

type CourseItem = { id: string; name: string; students: number };
type QueueItem = {
  assessment_id: string;
  session_id: string;
  student: string;
  scenario: string;
  mode: string;
  status: string;
  overall: number | null;
  flags: string[];
  is_mock: boolean;
  created_at: string;
};

export default async function TeachPage() {
  await requireRole("professor", "admin");
  const [courses, queue, specializations] = await Promise.all([
    api<CourseItem[]>("/api/v1/teach/courses"),
    api<QueueItem[]>("/api/v1/teach/review-queue"),
    api<Specialization[]>("/api/v1/specializations"),
  ]);
  const needsReview = queue.filter((q) => q.status !== "reviewed");

  return (
    <>
      <PageHeader
        title="Teaching"
        subtitle="Manage courses, review assessments and edit educational content."
        actions={
          <>
            <ButtonLink href="/teach/scenarios" variant="secondary">
              Scenarios &amp; rubrics
            </ButtonLink>
            <ButtonLink href="/teach/resources" variant="secondary">
              Course resources
            </ButtonLink>
          </>
        }
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <SectionTitle>Assessments to review ({needsReview.length})</SectionTitle>
          {queue.length === 0 ? (
            <EmptyState title="Nothing to review">Assessments of students in your courses appear here.</EmptyState>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500 dark:bg-slate-900">
                  <tr>
                    <th className="px-3 py-2">Student</th>
                    <th className="px-3 py-2">Scenario</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2 text-right">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {queue.map((q) => (
                    <tr key={q.assessment_id}>
                      <td className="px-3 py-2">
                        <Link href={`/teach/assessments/${q.assessment_id}`} className="font-medium text-blue-800 hover:underline dark:text-blue-300">
                          {q.student}
                        </Link>
                        <span className="block text-xs text-slate-500">{dateTime(q.created_at)}</span>
                      </td>
                      <td className="px-3 py-2">
                        {q.scenario}
                        <span className="block text-xs text-slate-500">{titleCase(q.mode)}</span>
                      </td>
                      <td className="px-3 py-2">
                        <Badge tone={q.status === "reviewed" ? "teal" : q.status === "needs_review" ? "amber" : "slate"}>
                          {titleCase(q.status)}
                        </Badge>
                        {q.flags.includes("possible_manipulation_attempt") ? (
                          <span className="ml-1">
                            <Badge tone="red">Flagged</Badge>
                          </span>
                        ) : null}
                      </td>
                      <td className={`px-3 py-2 text-right font-semibold ${scoreTone(q.overall)}`}>{score(q.overall)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <section>
          <SectionTitle>Your courses</SectionTitle>
          <ul className="mb-4 space-y-2">
            {courses.length === 0 ? <li className="text-sm text-slate-500">No courses yet.</li> : null}
            {courses.map((c) => (
              <li key={c.id}>
                <Link href={`/teach/courses/${c.id}`} className="block">
                  <Card className="!p-3 hover:border-blue-300 dark:hover:border-blue-800">
                    <p className="font-medium">{c.name}</p>
                    <p className="text-xs text-slate-500">{c.students} students</p>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
          <Card>
            <p className="mb-2 text-sm font-semibold">Create a course</p>
            <StatefulForm action={createCourseAction} submitLabel="Create course">
              <Field label="Course name" htmlFor="name">
                <input id="name" name="name" required minLength={2} maxLength={200} className={inputClass} />
              </Field>
              <Field label="Specialization (optional)" htmlFor="specialization_code">
                <select id="specialization_code" name="specialization_code" className={inputClass} defaultValue="">
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
