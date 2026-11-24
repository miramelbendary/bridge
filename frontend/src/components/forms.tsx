"use client";

import { type ReactNode, useActionState } from "react";
import { useFormStatus } from "react-dom";

import { Alert, Button, buttonStyles, cx } from "./ui";

type State = { error?: string; message?: string; errors?: string[] };

export function StatefulForm({
  action,
  children,
  className,
  submitLabel,
  submitVariant = "primary",
}: {
  action: (state: State, formData: FormData) => Promise<State>;
  children: ReactNode;
  className?: string;
  submitLabel?: string;
  submitVariant?: keyof typeof buttonStyles;
}) {
  const [state, formAction] = useActionState(action, {});
  return (
    <form action={formAction} className={cx("space-y-3", className)}>
      {state.error ? (
        <Alert tone="error">
          <p>{state.error}</p>
          {state.errors?.length ? (
            <ul className="mt-2 list-disc space-y-0.5 pl-5 text-xs">
              {state.errors.slice(0, 30).map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          ) : null}
        </Alert>
      ) : null}
      {state.message ? <Alert tone="success">{state.message}</Alert> : null}
      {children}
      {submitLabel ? <SubmitButton variant={submitVariant}>{submitLabel}</SubmitButton> : null}
    </form>
  );
}

export function SubmitButton({
  children,
  variant = "primary",
  name,
  value,
}: {
  children: ReactNode;
  variant?: keyof typeof buttonStyles;
  name?: string;
  value?: string;
}) {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" variant={variant} disabled={pending} name={name} value={value}>
      {pending ? "Working…" : children}
    </Button>
  );
}

export function PrintButton() {
  return (
    <Button type="button" variant="secondary" onClick={() => window.print()} className="print:hidden">
      Print / save as PDF
    </Button>
  );
}
