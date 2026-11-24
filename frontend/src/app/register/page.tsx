import type { Metadata } from "next";

import { registerAction } from "@/app/actions/auth";
import { AuthForm } from "@/components/auth-form";
import { AuthShell } from "@/components/auth-shell";

export const metadata: Metadata = { title: "Create account · BRIDGE" };

export default function RegisterPage() {
  return (
    <AuthShell
      title="Create your student account"
      subtitle="Practise real workplace situations and get evidence-based feedback."
    >
      <AuthForm mode="register" action={registerAction} />
    </AuthShell>
  );
}
