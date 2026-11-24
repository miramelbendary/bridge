import { ApiError, apiFetch } from "@/lib/api";
import { getSessionToken } from "@/lib/session";

/** Proxies the CSV export so the access token never leaves the server. The backend enforces
 * that only the course owner (or an administrator) can export. */
export async function GET(_request: Request, ctx: RouteContext<"/api/export/[courseId]">) {
  const { courseId } = await ctx.params;
  if (!/^[0-9a-f-]{36}$/i.test(courseId)) return new Response("Not found", { status: 404 });
  const token = await getSessionToken();
  if (!token) return new Response("Not authenticated", { status: 401 });
  try {
    const upstream = await apiFetch<Response>(`/api/v1/teach/courses/${courseId}/export.csv`, { token, raw: true });
    return new Response(await upstream.text(), {
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": upstream.headers.get("Content-Disposition") ?? 'attachment; filename="bridge-course.csv"',
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 502;
    return new Response(status === 404 ? "Not found" : "Export failed", { status });
  }
}
