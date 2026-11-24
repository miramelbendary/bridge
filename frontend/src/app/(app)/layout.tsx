import type { ReactNode } from "react";
import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { Skeleton } from "@/components/ui";

function ShellFallback() {
  return (
    <>
      <div className="h-14 border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900" />
      <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6" aria-live="polite">
        <span className="sr-only">Loading…</span>
        <Skeleton lines={5} />
      </div>
    </>
  );
}

/** Everything under (app) reads the session cookie, so it streams in behind one Suspense
 * boundary (required with Cache Components). */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<ShellFallback />}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
