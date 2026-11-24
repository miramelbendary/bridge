import Link from "next/link";
import type { ReactNode } from "react";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <Link href="/" className="text-sm font-semibold tracking-wide text-blue-700 dark:text-blue-400">
          BRIDGE
        </Link>
        <h1 className="mt-4 text-2xl font-semibold text-slate-900 dark:text-slate-100">{title}</h1>
        <p className="mt-1 mb-6 text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>
        {children}
      </div>
    </main>
  );
}
