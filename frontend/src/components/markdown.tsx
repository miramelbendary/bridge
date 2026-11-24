import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders scenario documents. Raw HTML in the source is NOT rendered (react-markdown default),
 * so scenario content cannot inject scripts. */
export function Markdown({ children, dir = "ltr" }: { children: string; dir?: "ltr" | "rtl" }) {
  return (
    <div
      dir={dir}
      className="prose-bridge space-y-3 text-sm leading-relaxed text-slate-800 dark:text-slate-200 [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:font-semibold [&_li]:ml-5 [&_ol]:list-decimal [&_strong]:font-semibold [&_table]:w-full [&_table]:border-collapse [&_td]:border [&_td]:border-slate-200 [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-slate-200 [&_th]:bg-slate-50 [&_th]:px-2 [&_th]:py-1 [&_th]:text-left dark:[&_td]:border-slate-700 dark:[&_th]:border-slate-700 dark:[&_th]:bg-slate-800 [&_ul]:list-disc"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
