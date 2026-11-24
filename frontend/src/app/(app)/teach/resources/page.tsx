import type { Metadata } from "next";

import { deleteResourceAction, uploadResourceAction } from "@/app/actions/manage";
import { StatefulForm } from "@/components/forms";
import { Badge, Card, EmptyState, Field, PageHeader, SectionTitle, inputClass } from "@/components/ui";
import type { Specialization } from "@/lib/api";
import { api, requireRole } from "@/lib/auth";
import { dateTime } from "@/lib/format";

export const metadata: Metadata = { title: "Course resources · BRIDGE" };

type Resource = { id: string; title: string; filename: string; visibility: string; version: number; chunks: number; created_at: string };

export default async function ResourcesPage() {
  await requireRole("professor", "admin");
  const [resources, specializations] = await Promise.all([
    api<Resource[]>("/api/v1/teach/resources"),
    api<Specialization[]>("/api/v1/specializations"),
  ]);
  return (
    <>
      <PageHeader
        title="Course resources"
        subtitle="Approved teaching materials are split into passages and cited in student feedback. Professor-only material is never shown to students."
      />
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <SectionTitle>Uploaded materials</SectionTitle>
          {resources.length === 0 ? (
            <EmptyState title="No resources yet" />
          ) : (
            <ul className="space-y-2">
              {resources.map((r) => (
                <li key={r.id}>
                  <Card className="!p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-medium">
                          {r.title} <span className="text-xs text-slate-500">v{r.version}</span>
                        </p>
                        <p className="text-xs text-slate-500">
                          {r.filename} · {r.chunks} passages · {dateTime(r.created_at)}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge tone={r.visibility === "students" ? "teal" : "amber"}>
                          {r.visibility === "students" ? "Visible to students" : "Professors only"}
                        </Badge>
                        <form action={deleteResourceAction}>
                          <input type="hidden" name="resource_id" value={r.id} />
                          <button type="submit" className="text-xs text-red-700 hover:underline dark:text-red-400">
                            Delete
                          </button>
                        </form>
                      </div>
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>
        <Card className="h-fit">
          <SectionTitle>Upload material</SectionTitle>
          <StatefulForm action={uploadResourceAction} submitLabel="Upload">
            <Field label="Title" htmlFor="title">
              <input id="title" name="title" required minLength={2} maxLength={300} className={inputClass} />
            </Field>
            <Field label="File (.txt or .md, UTF-8, max 2 MB)" htmlFor="file" hint="Only upload material you are authorised to use.">
              <input id="file" name="file" type="file" accept=".txt,.md,text/plain,text/markdown" required className="block w-full max-w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm dark:file:bg-slate-800 dark:file:text-slate-100" />
            </Field>
            <Field label="Visibility" htmlFor="visibility">
              <select id="visibility" name="visibility" className={inputClass} defaultValue="students">
                <option value="students">Students may see citations</option>
                <option value="professors">Professors only (answer keys)</option>
              </select>
            </Field>
            <Field label="Specialization" htmlFor="specialization_code">
              <select id="specialization_code" name="specialization_code" className={inputClass} defaultValue="">
                <option value="">All specializations</option>
                {specializations.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>
          </StatefulForm>
        </Card>
      </div>
    </>
  );
}
