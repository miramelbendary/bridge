import type { Metadata } from "next";
import Link from "next/link";

import { Badge, Card, PageHeader } from "@/components/ui";
import type { ScenarioSummary } from "@/lib/api";
import { api, requireRole } from "@/lib/auth";
import { titleCase } from "@/lib/format";

export const metadata: Metadata = { title: "Scenario authoring · BRIDGE" };

export default async function AuthoringPage() {
  await requireRole("professor", "admin");
  const scenarios = await api<ScenarioSummary[]>("/api/v1/scenarios");
  return (
    <>
      <PageHeader
        title="Scenarios & rubrics"
        subtitle="Edits create a new immutable version. Attempts in progress keep the version they started with. Administrators publish."
      />
      <ul className="grid gap-3 md:grid-cols-2">
        {scenarios.map((s) => (
          <li key={s.slug}>
            <Link href={`/teach/scenarios/${s.slug}`} className="block">
              <Card className="!p-4 hover:border-blue-300 dark:hover:border-blue-800">
                <div className="flex flex-wrap gap-2">
                  <Badge tone="blue">{s.specialization.name}</Badge>
                  <Badge tone={s.status === "published" ? "teal" : "amber"}>{titleCase(s.status)}</Badge>
                  <Badge>v{s.version}</Badge>
                </div>
                <p className="mt-2 font-medium">{s.title}</p>
                <p className="text-xs text-slate-500">{s.slug}</p>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
