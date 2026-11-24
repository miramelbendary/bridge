"use client";

import Link from "next/link";
import { useActionState } from "react";

import type { AuthFormState } from "@/app/actions/auth";

type Props = {
  mode: "login" | "register";
  action: (state: AuthFormState, formData: FormData) => Promise<AuthFormState>;
  notice?: string;
};

const inputClass =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm " +
  "focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/30 " +
  "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

export function AuthForm({ mode, action, notice }: Props) {
  const [state, formAction, pending] = useActionState(action, {});
  const isRegister = mode === "register";

  return (
    <form action={formAction} className="space-y-4" noValidate={false}>
      {notice && !state.error ? (
        <p className="rounded-md bg-sky-50 px-3 py-2 text-sm text-sky-900 dark:bg-sky-950 dark:text-sky-100">
          {notice}
        </p>
      ) : null}
      {state.error ? (
        <p
          role="alert"
          className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-200"
        >
          {state.error}
        </p>
      ) : null}

      {isRegister ? (
        <div className="space-y-1">
          <label htmlFor="display_name" className="block text-sm font-medium">
            Display name
          </label>
          <input
            id="display_name"
            name="display_name"
            required
            maxLength={120}
            autoComplete="nickname"
            defaultValue={state.displayName}
            className={inputClass}
          />
        </div>
      ) : null}

      <div className="space-y-1">
        <label htmlFor="email" className="block text-sm font-medium">
          University email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
          defaultValue={state.email}
          className={inputClass}
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="password" className="block text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          required
          minLength={isRegister ? 10 : undefined}
          maxLength={128}
          autoComplete={isRegister ? "new-password" : "current-password"}
          className={inputClass}
        />
        {isRegister ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">At least 10 characters.</p>
        ) : null}
      </div>

      {isRegister ? (
        <div className="space-y-1">
          <label htmlFor="confirm_password" className="block text-sm font-medium">
            Confirm password
          </label>
          <input
            id="confirm_password"
            name="confirm_password"
            type="password"
            required
            minLength={10}
            maxLength={128}
            autoComplete="new-password"
            className={inputClass}
          />
        </div>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-md bg-blue-700 px-4 py-2 font-medium text-white hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-700/40 disabled:opacity-60"
      >
        {pending ? "Please wait…" : isRegister ? "Create account" : "Sign in"}
      </button>

      <p className="text-center text-sm text-slate-600 dark:text-slate-400">
        {isRegister ? (
          <>
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-teal-700 hover:underline dark:text-teal-400">
              Sign in
            </Link>
          </>
        ) : (
          <>
            New to BRIDGE?{" "}
            <Link href="/register" className="font-medium text-teal-700 hover:underline dark:text-teal-400">
              Create an account
            </Link>
          </>
        )}
      </p>
    </form>
  );
}
