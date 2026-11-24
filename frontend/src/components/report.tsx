import type { ReactNode } from "react";

import type { AssessmentData } from "@/lib/api";
import { score, scoreTone, simTime, titleCase } from "@/lib/format";

import { Alert, Badge, Card, Meter, SectionTitle } from "./ui";

const FLAG_TEXT: Record<string, string> = {
  possible_manipulation_attempt:
    "Some submitted text looked like an attempt to instruct the assessor. It was ignored and this assessment is flagged for professor review.",
  ai_unavailable_used_mock_evaluator: "The AI assessor was unavailable, so the transparent rule-based evaluator was used.",
};

export function AssessmentReport({ a, extra }: { a: AssessmentData; extra?: (criterionId: string) => ReactNode }) {
  const r = a.report;
  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm text-slate-500">Scenario outcome</p>
            <h2 className="text-xl font-semibold">{r.outcome.title}</h2>
            <p className="mt-1 max-w-2xl text-sm text-slate-700 dark:text-slate-300">{r.outcome.description}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge tone="blue">{titleCase(a.mode)} mode</Badge>
              <Badge>{titleCase(a.difficulty)}</Badge>
              <Badge tone={a.status === "reviewed" ? "teal" : a.status === "needs_review" ? "amber" : "slate"}>
                {a.status === "reviewed" ? "Reviewed by professor" : a.status === "needs_review" ? "Awaiting professor review" : "AI-generated, not yet reviewed"}
              </Badge>
              {a.is_mock ? <Badge tone="amber">Offline mock evaluator</Badge> : <Badge>{a.model}</Badge>}
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-slate-500">Overall</p>
            <p className={`text-5xl font-semibold ${scoreTone(a.final_overall)}`}>{score(a.final_overall)}</p>
            <p className="text-xs text-slate-500">
              out of 100 · based on {r.assessed_weight_percent}% of the rubric
              {a.original_overall !== a.final_overall ? ` · AI original ${score(a.original_overall)}` : ""}
            </p>
          </div>
        </div>
        {a.flags.filter((f) => FLAG_TEXT[f]).map((f) => (
          <div key={f} className="mt-3">
            <Alert tone="warning">{FLAG_TEXT[f]}</Alert>
          </div>
        ))}
        {r.not_assessed.length ? (
          <div className="mt-3">
            <Alert tone="info">
              Not assessed (insufficient evidence — this is not a failing grade): {r.not_assessed.join(", ")}.
            </Alert>
          </div>
        ) : null}
        <p className="mt-4 text-sm leading-relaxed">{r.overall_feedback}</p>
      </Card>

      <section>
        <SectionTitle>Competency scores</SectionTitle>
        <div className="space-y-3">
          {a.criteria.map((c) => (
            <Card key={c.criterion_id} className="!p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="max-w-2xl">
                  <p className="font-medium">
                    {c.name} <span className="text-xs font-normal text-slate-500">· weight {c.weight}%</span>
                  </p>
                  <p className="text-xs text-slate-500">{c.description}</p>
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-semibold ${scoreTone(c.final_score)}`}>
                    {c.insufficient_evidence ? "n/a" : score(c.final_score)}
                  </p>
                  <p className="text-xs text-slate-500">{c.insufficient_evidence ? "Insufficient evidence" : c.level_label}</p>
                </div>
              </div>
              {!c.insufficient_evidence && c.final_score !== null ? (
                <div className="mt-2">
                  <Meter value={c.final_score} label={`${c.name} score`} />
                </div>
              ) : null}
              <p className="mt-3 text-sm">{c.explanation}</p>
              <p className="mt-1 text-xs text-slate-500">
                Uncertainty: {c.uncertainty}
                {c.objective_score !== null ? ` · rule-based part ${score(c.objective_score)}` : ""}
                {c.qualitative_score !== null ? ` · qualitative part ${score(c.qualitative_score)}` : ""}
                {c.original_score !== c.final_score ? ` · corrected from ${score(c.original_score)}` : ""}
              </p>
              {c.evidence.length ? (
                <details className="mt-2">
                  <summary className="cursor-pointer text-sm font-medium text-blue-800 dark:text-blue-300">
                    Evidence from your work ({c.evidence.length})
                  </summary>
                  <ul className="mt-2 space-y-2">
                    {c.evidence.map((e) => (
                      <li key={e.ref} className="rounded-md bg-slate-50 p-2 text-sm dark:bg-slate-800">
                        <span className="text-xs font-semibold text-slate-500">
                          {e.ref} · {e.summary}
                        </span>
                        <p className="mt-1 whitespace-pre-wrap" dir="auto">
                          {e.excerpt}
                          {e.excerpt.length >= 240 ? "…" : ""}
                        </p>
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
              {c.weaknesses.length || c.improvements.length ? (
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {c.weaknesses.length ? (
                    <div>
                      <p className="text-xs font-semibold uppercase text-slate-500">Weaknesses</p>
                      <ul className="list-disc pl-5 text-sm">
                        {c.weaknesses.map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {c.improvements.length ? (
                    <div>
                      <p className="text-xs font-semibold uppercase text-slate-500">How to improve</p>
                      <ul className="list-disc pl-5 text-sm">
                        {c.improvements.map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : null}
              {extra ? extra(c.criterion_id) : null}
            </Card>
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>Strengths</SectionTitle>
          {r.strengths.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {r.strengths.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No clear strengths were evidenced in this attempt.</p>
          )}
        </Card>
        <Card>
          <SectionTitle>Final situation</SectionTitle>
          <ul className="space-y-1 text-sm">
            {r.final_variables.map((v) => (
              <li key={v.label} className="flex justify-between gap-4">
                <span>{v.label}</span>
                <span className="font-medium tabular-nums">
                  {v.value.toLocaleString("en-GB")} {v.unit}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card>
        <SectionTitle>Your key decisions and their consequences</SectionTitle>
        {r.key_decisions.length === 0 ? (
          <p className="text-sm text-slate-500">No decisions were recorded.</p>
        ) : (
          <ol className="space-y-3">
            {r.key_decisions.map((d, i) => (
              <li key={i} className="border-l-2 border-blue-200 pl-3 text-sm dark:border-blue-900">
                <p>
                  <span className="text-xs text-slate-500 tabular-nums">{simTime(d.minute)}</span>{" "}
                  <span className="font-medium">{d.label}</span>
                  {d.via === "conversation" ? <span className="text-xs text-slate-500"> (via conversation)</span> : null}
                </p>
                {d.justification ? <p className="text-slate-600 dark:text-slate-400">Your reasoning: “{d.justification}”</p> : null}
                <p>{d.consequence}</p>
                {d.effects.length ? (
                  <p className="text-xs text-slate-500">
                    {d.effects.map((e) => `${e.label}: ${e.before} → ${e.after}${e.unit === "%" ? "%" : ` ${e.unit}`}`).join(" · ")}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>Alternative reasonable approaches</SectionTitle>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {r.alternative_approaches.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </Card>
        <Card>
          <SectionTitle>Concepts to revise</SectionTitle>
          {r.concepts_to_revise.length === 0 ? (
            <p className="text-sm text-slate-500">No specific concepts flagged for revision.</p>
          ) : (
            <ul className="space-y-3 text-sm">
              {r.concepts_to_revise.map((c) => (
                <li key={`${c.criterion}-${c.concept}`}>
                  <p className="font-medium">{c.concept}</p>
                  <p className="text-xs text-slate-500">Linked to: {c.criterion}</p>
                  {c.resources.length ? (
                    c.resources.map((res) => (
                      <blockquote key={res.title + res.heading} className="mt-1 border-l-2 border-teal-300 pl-2 text-xs text-slate-600 dark:text-slate-400">
                        <span className="font-semibold">
                          {res.title}
                          {res.heading ? ` — ${res.heading}` : ""}
                        </span>
                        <span className="block">{res.excerpt}…</span>
                      </blockquote>
                    ))
                  ) : (
                    <p className="text-xs text-slate-500">No approved course material is available for this concept yet.</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {a.reviews.length ? (
        <Card>
          <SectionTitle>Professor review history</SectionTitle>
          <ul className="space-y-2 text-sm">
            {a.reviews.map((rv, i) => (
              <li key={i}>
                {rv.criterion_id ? (
                  <span className="font-medium">
                    {titleCase(rv.criterion_id)}: {score(rv.previous_score)} → {rv.new_score === null ? "n/a" : score(rv.new_score)}
                  </span>
                ) : (
                  <span className="font-medium">General review</span>
                )}
                <span className="block text-slate-600 dark:text-slate-400">“{rv.justification}”</span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <p className="text-xs text-slate-500">
        {r.disclaimer} {r.review_status}
      </p>
    </div>
  );
}
