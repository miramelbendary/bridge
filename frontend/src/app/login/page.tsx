import type { Metadata } from "next";
import { Suspense } from "react";

import { loginAction } from "@/app/actions/auth";
import { AuthForm } from "@/components/auth-form";
import { AuthShell } from "@/components/auth-shell";

export const metadata: Metadata = { title: "Sign in · BRIDGE" };

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

export default function LoginPage(props: PageProps<"/login">) {
  return (
    <AuthShell title="Sign in" subtitle="Continue to your simulated workplace.">
      <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
        <LoginForm searchParams={props.searchParams as Promise<{ expired?: string }>} />
      </Suspense>
    </AuthShell>
  );
}
