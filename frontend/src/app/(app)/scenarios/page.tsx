import type { Metadata } from "next";
import Link from "next/link";

import { Badge, Card, EmptyState, PageHeader, cx } from "@/components/ui";
import type { ScenarioSummary, Specialization } from "@/lib/api";
import { api } from "@/lib/auth";
import { titleCase } from "@/lib/format";

export const metadata: Metadata = { title: "Scenarios · BRIDGE" };

export default async function ScenariosPage(props: PageProps<"/scenarios">) {
  const params = (await props.searchParams) as { specialization?: string };
  const selected = typeof params.specialization === "string" ? params.specialization : "";
  const [scenarios, specializations] = await Promise.all([
    api<ScenarioSummary[]>("/api/v1/scenarios"),
    api<Specialization[]>("/api/v1/specializations"),
  ]);
  const shown = selected ? scenarios.filter((s) => s.specialization.code === selected) : scenarios;

  return (
    <>
      <PageHeader title="Scenario library" subtitle="Choose a simulated workplace. All organisations and people are fictional." />
      <nav aria-label="Filter by specialization" className="mb-6 flex flex-wrap gap-2">
        {[{ code: "", name: "All" }, ...specializations].map((s) => (
          <Link
            key={s.code || "all"}
            href={s.code ? `/scenarios?specialization=${s.code}` : "/scenarios"}
            aria-current={selected === s.code ? "true" : undefined}
            className={cx(
              "rounded-full border px-3 py-1 text-sm",
              selected === s.code
                ? "border-blue-700 bg-blue-700 text-white"
                : "border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800",
            )}
          >
            {s.name}
          </Link>
        ))}
      </nav>
      {shown.length === 0 ? (
        <EmptyState title="No scenarios here yet" />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {shown.map((s) => (
            <li key={s.slug}>
              <Link href={`/scenarios/${s.slug}`} className="block h-full">
                <Card className="h-full hover:border-blue-300 dark:hover:border-blue-800">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="blue">{s.specialization.name}</Badge>
                    <Badge>~{s.estimated_minutes} min</Badge>
                    {s.status !== "published" ? <Badge tone="amber">{titleCase(s.status)}</Badge> : null}
                  </div>
                  <h2 className="mt-3 text-lg font-semibold">{s.title}</h2>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{s.summary}</p>
                  <p className="mt-3 text-xs text-slate-500">
                    Practises: {s.competencies.map(titleCase).join(", ")}
                  </p>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
