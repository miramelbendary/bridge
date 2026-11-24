import { DefinitionEditor, RubricEditor } from "@/components/editors";
import { Badge, Card, PageHeader, SectionTitle } from "@/components/ui";
import { api, requireRole } from "@/lib/auth";
import { dateTime, titleCase } from "@/lib/format";

type DefinitionData = {
  slug: string;
  status: string;
  version: number;
  definition: { title: string; rubric: { title: string; criteria: never[] } } & Record<string, unknown>;
  versions: { version: number; change_note: string; created_at: string }[];
};

export default async function ScenarioEditorPage(props: PageProps<"/teach/scenarios/[slug]">) {
  await requireRole("professor", "admin");
  const { slug } = await props.params;
  const data = await api<DefinitionData>(`/api/v1/teach/scenarios/${encodeURIComponent(slug)}/definition`);
  return (
    <>
      <PageHeader
        title={data.definition.title}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <Badge tone={data.status === "published" ? "teal" : "amber"}>{titleCase(data.status)}</Badge>
            <span>Current version {data.version}</span>
          </span>
        }
      />
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <Card>
            <SectionTitle>Rubric editor</SectionTitle>
            <RubricEditor key={data.version} slug={data.slug} initial={data.definition.rubric} />
          </Card>
          <Card>
            <SectionTitle>Full scenario editor</SectionTitle>
            <p className="mb-3 text-sm text-slate-600 dark:text-slate-400">
              Edit documents, characters, events, actions, consequences and outcomes. All companies, people and facts must be fictional
              and reviewed by a subject specialist before use.
            </p>
            <DefinitionEditor key={data.version} initial={data.definition} />
          </Card>
        </div>
        <Card className="h-fit">
          <SectionTitle>Version history</SectionTitle>
          <ol className="space-y-2 text-sm">
            {data.versions.map((v) => (
              <li key={v.version}>
                <span className="font-medium">v{v.version}</span> <span className="text-xs text-slate-500">{dateTime(v.created_at)}</span>
                <span className="block text-slate-600 dark:text-slate-400">{v.change_note || "—"}</span>
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </>
  );
}
