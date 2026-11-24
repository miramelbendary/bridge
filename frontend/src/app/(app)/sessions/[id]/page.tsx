import { Workplace } from "@/components/workplace/workplace";
import type { SessionView } from "@/lib/api";
import { api } from "@/lib/auth";

export default async function SessionPage(props: PageProps<"/sessions/[id]">) {
  const { id } = await props.params;
  const view = await api<SessionView>(`/api/v1/sessions/${encodeURIComponent(id)}`);
  return <Workplace key={`${view.session_id}-${view.status}`} initial={view} />;
}
