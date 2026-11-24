import type { Metadata } from "next";
import Link from "next/link";

import { Badge, EmptyState, PageHeader } from "@/components/ui";
import type { SessionListItem } from "@/lib/api";
import { api } from "@/lib/auth";
import { dateTime, score, scoreTone, titleCase } from "@/lib/format";

export const metadata: Metadata = { title: "History · BRIDGE" };

export default async function HistoryPage() {
  const sessions = await api<SessionListItem[]>("/api/v1/sessions");
  return (
    <>
      <PageHeader title="Simulation history" subtitle="Every attempt is kept with the exact scenario version you used." />
      {sessions.length === 0 ? (
        <EmptyState title="No attempts yet">
          <Link href="/scenarios" className="text-blue-700 hover:underline">
            Start your first simulation
          </Link>
        </EmptyState>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500 dark:bg-slate-900">
              <tr>
                <th className="px-4 py-2">Scenario</th>
                <th className="px-4 py-2">Mode</th>
                <th className="px-4 py-2">Started</th>
                <th className="px-4 py-2">Outcome</th>
                <th className="px-4 py-2 text-right">Score</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {sessions.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-2">
                    <span className="font-medium">{s.scenario_title}</span>
                    <span className="block text-xs text-slate-500">
                      {s.specialization} · v{s.scenario_version}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {titleCase(s.mode)}
                    <span className="block text-xs text-slate-500">{titleCase(s.difficulty)}</span>
                  </td>
                  <td className="px-4 py-2">{dateTime(s.started_at)}</td>
                  <td className="px-4 py-2">
                    {s.status === "active" ? <Badge tone="blue">In progress</Badge> : s.status === "abandoned" ? <Badge>Abandoned</Badge> : s.outcome}
                    {s.assessment_status === "reviewed" ? (
                      <span className="ml-2">
                        <Badge tone="teal">Reviewed by professor</Badge>
                      </span>
                    ) : null}
                  </td>
                  <td className={`px-4 py-2 text-right text-lg font-semibold ${scoreTone(s.overall_score)}`}>{score(s.overall_score)}</td>
                  <td className="px-4 py-2 text-right">
                    {s.status === "active" ? (
                      <Link className="text-blue-700 hover:underline dark:text-blue-300" href={`/sessions/${s.id}`}>
                        Resume
                      </Link>
                    ) : s.assessment_id ? (
                      <Link className="text-blue-700 hover:underline dark:text-blue-300" href={`/sessions/${s.id}/report`}>
                        Report
                      </Link>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
