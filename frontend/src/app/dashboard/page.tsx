import type { Metadata } from "next";
import { Suspense } from "react";

import { logoutAction } from "@/app/actions/auth";
import { getCurrentUser, getSpecializations } from "@/lib/auth";

export const metadata: Metadata = { title: "Dashboard · BRIDGE" };

const ROLE_LABEL = { student: "Student", professor: "Professor", admin: "Administrator" } as const;

async function DashboardContent() {
  const [user, specializations] = await Promise.all([getCurrentUser(), getSpecializations()]);
  const name = user.profile?.display_name ?? user.email;

  return (
    <>
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400">Signed in as {user.email}</p>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
            Welcome, {name}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-teal-50 px-3 py-1 text-sm font-medium text-teal-800 dark:bg-teal-950 dark:text-teal-200">
            {ROLE_LABEL[user.role]}
          </span>
          <form action={logoutAction}>
            <button
              type="submit"
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Sign out
            </button>
          </form>
        </div>
      </header>

      <section className="mt-10" aria-labelledby="specializations-heading">
        <h2 id="specializations-heading" className="text-lg font-semibold">
          Specializations
        </h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Loaded live from the BRIDGE API. Scenario selection arrives in a later phase.
        </p>
        {specializations.length === 0 ? (
          <p className="mt-4 text-sm text-slate-500">No specializations are available yet.</p>
        ) : (
          <ul className="mt-4 grid gap-4 sm:grid-cols-3">
            {specializations.map((s) => (
              <li
                key={s.id}
                className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
              >
                <h3 className="font-medium text-blue-800 dark:text-blue-300">{s.name}</h3>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{s.description}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

export default function DashboardPage() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6">
      <Suspense
        fallback={
          <p className="text-sm text-slate-500" aria-live="polite">
            Loading your dashboard…
          </p>
        }
      >
        <DashboardContent />
      </Suspense>
    </main>
  );
}
