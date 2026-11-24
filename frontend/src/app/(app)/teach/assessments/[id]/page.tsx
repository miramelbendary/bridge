import { reviewAction } from "@/app/actions/manage";
import { PrintButton, StatefulForm } from "@/components/forms";
import { AssessmentReport } from "@/components/report";
import { ButtonLink, Card, Field, PageHeader, SectionTitle, inputClass } from "@/components/ui";
import type { AssessmentData } from "@/lib/api";
import { api, requireRole } from "@/lib/auth";
import { dateTime } from "@/lib/format";

export default async function ReviewPage(props: PageProps<"/teach/assessments/[id]">) {
  await requireRole("professor", "admin");
  const { id } = await props.params;
  const a = await api<AssessmentData>(`/api/v1/teach/assessments/${encodeURIComponent(id)}`);

  const override = (criterionId: string) => (
    <details className="mt-3 print:hidden">
      <summary className="cursor-pointer text-sm font-medium text-teal-800 dark:text-teal-300">Correct this score</summary>
      <StatefulForm action={reviewAction} submitLabel="Save correction" submitVariant="teal" className="mt-2">
        <input type="hidden" name="assessment_id" value={a.id} />
        <input type="hidden" name="criterion_id" value={criterionId} />
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="New score (0–100)" htmlFor={`s-${criterionId}`}>
            <input id={`s-${criterionId}`} name="new_score" type="number" min={0} max={100} step={0.5} className={inputClass} />
          </Field>
          <label className="mt-6 flex items-center gap-2 text-sm">
            <input type="checkbox" name="insufficient" /> Insufficient evidence
          </label>
        </div>
        <Field label="Justification (required, kept in the audit history)" htmlFor={`j-${criterionId}`}>
          <textarea id={`j-${criterionId}`} name="justification" required minLength={10} rows={2} className={inputClass} />
        </Field>
      </StatefulForm>
    </details>
  );

  return (
    <>
      <PageHeader
        title="Assessment review"
        subtitle={`${a.report.scenario_title} · assessed ${dateTime(a.created_at)} · ${a.is_mock ? "mock evaluator" : a.model}`}
        actions={
          <>
            <PrintButton />
            <ButtonLink href={`/sessions/${a.session_id}`} variant="secondary">
              Open workplace (read-only)
            </ButtonLink>
            <ButtonLink href={`/teach/students/${a.student_id}`} variant="secondary">
              Student
            </ButtonLink>
          </>
        }
      />
      <Card className="mb-6 print:hidden">
        <SectionTitle>Confirm without changes</SectionTitle>
        <StatefulForm action={reviewAction} submitLabel="Mark as reviewed" submitVariant="teal">
          <input type="hidden" name="assessment_id" value={a.id} />
          <Field label="Comment (required)" htmlFor="general">
            <textarea id="general" name="justification" required minLength={10} rows={2} className={inputClass} />
          </Field>
        </StatefulForm>
        <p className="mt-2 text-xs text-slate-500">
          Corrections never overwrite the original AI result: both are kept and every change is audited.
        </p>
      </Card>
      <AssessmentReport a={a} extra={override} />
    </>
  );
}
