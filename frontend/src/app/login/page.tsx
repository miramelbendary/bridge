import type { Metadata } from "next";
import { Suspense } from "react";

import { loginAction } from "@/app/actions/auth";
import { AuthForm } from "@/components/auth-form";
import { AuthShell } from "@/components/auth-shell";

export const metadata: Metadata = { title: "Sign in · BRIDGE" };

const DEMO_ACCOUNTS = [
  ["Student", "demo.student@example.com"],
  ["Professor", "demo.professor@example.com"],
  ["Administrator", "demo.admin@example.com"],
] as const;

async function LoginForm({ searchParams }: { searchParams: Promise<{ expired?: string }> }) {
  const { expired } = await searchParams;
  return (
    <AuthForm
      mode="login"
      action={loginAction}
      notice={expired ? "Your session has expired. Please sign in again." : undefined}
    />
  );
}

function DemoAccounts() {
  // Only shown on local/demo installs (BRIDGE_DEMO_MODE=1). Fictional accounts created by `seed-demo`.
  if (process.env.BRIDGE_DEMO_MODE !== "1") return null;
  return (
    <div className="mt-6 rounded-md border border-dashed border-teal-300 bg-teal-50 p-3 text-xs text-teal-900 dark:border-teal-800 dark:bg-teal-950 dark:text-teal-100">
      <p className="font-semibold">Demo accounts (local demo only)</p>
      <ul className="mt-1 space-y-0.5">
        {DEMO_ACCOUNTS.map(([role, email]) => (
          <li key={email}>
            {role}: <span className="font-mono">{email}</span>
          </li>
        ))}
      </ul>
      <p className="mt-1">
        Password for all: <span className="font-mono">bridge-demo-2026</span>
      </p>
    </div>
  );
}

export default function LoginPage(props: PageProps<"/login">) {
  return (
    <AuthShell title="Sign in" subtitle="Continue to your simulated workplace.">
      <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
        <LoginForm searchParams={props.searchParams as Promise<{ expired?: string }>} />
        <DemoAccounts />
      </Suspense>
    </AuthShell>
  );
}
