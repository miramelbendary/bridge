import { PrintButton } from "@/components/forms";
import { AssessmentReport } from "@/components/report";
import { ButtonLink, PageHeader } from "@/components/ui";
import type { AssessmentData } from "@/lib/api";
import { api } from "@/lib/auth";
import { dateTime } from "@/lib/format";

export default async function ReportPage(props: PageProps<"/sessions/[id]/report">) {
  const { id } = await props.params;
  const a = await api<AssessmentData>(`/api/v1/sessions/${encodeURIComponent(id)}/assessment`);
  return (
    <>
      <PageHeader
        title={`Report: ${a.report.scenario_title}`}
        subtitle={`Assessed ${dateTime(a.created_at)}`}
        actions={
          <>
            <PrintButton />
            <ButtonLink href={`/sessions/${id}`} variant="secondary" className="print:hidden">
              Review the workplace
            </ButtonLink>
            <ButtonLink href="/profile" className="print:hidden">
              See my competencies
            </ButtonLink>
          </>
        }
      />
      <AssessmentReport a={a} />
    </>
  );
}
