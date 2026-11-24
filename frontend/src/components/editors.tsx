"use client";

import { useActionState, useState } from "react";

import { saveRubricAction, validateScenarioAction } from "@/app/actions/manage";

import { SubmitButton } from "./forms";
import { Alert, Field, cx, inputClass } from "./ui";

type Level = { score: number; label: string; descriptor: string };
type Criterion = {
  id: string;
  name: string;
  competency: string;
  weight: number;
  description: string;
  levels: Level[];
  [key: string]: unknown;
};
type Rubric = { title: string; criteria: Criterion[] };
type State = { error?: string; message?: string; errors?: string[] };

function Messages({ state }: { state: State }) {
  return (
    <>
      {state.error ? (
        <Alert tone="error">
          <p>{state.error}</p>
          {state.errors?.length ? (
            <ul className="mt-2 list-disc space-y-0.5 pl-5 text-xs">
              {state.errors.slice(0, 40).map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          ) : null}
        </Alert>
      ) : null}
      {state.message ? <Alert tone="success">{state.message}</Alert> : null}
    </>
  );
}

export function RubricEditor({ slug, initial }: { slug: string; initial: Rubric }) {
  const [rubric, setRubric] = useState<Rubric>(initial);
  const [state, action] = useActionState(saveRubricAction, {} as State);
  const total = rubric.criteria.reduce((sum, c) => sum + Number(c.weight || 0), 0);

  function update(i: number, patch: Partial<Criterion>) {
    setRubric((r) => ({ ...r, criteria: r.criteria.map((c, j) => (j === i ? { ...c, ...patch } : c)) }));
  }
  function updateLevel(i: number, li: number, patch: Partial<Level>) {
    setRubric((r) => ({
      ...r,
      criteria: r.criteria.map((c, j) =>
        j === i ? { ...c, levels: c.levels.map((lv, k) => (k === li ? { ...lv, ...patch } : lv)) } : c,
      ),
    }));
  }

  return (
    <form action={action} className="space-y-4">
      <input type="hidden" name="slug" value={slug} />
      <input type="hidden" name="rubric" value={JSON.stringify(rubric)} />
      <Messages state={state} />
      <p className={cx("text-sm font-medium", Math.abs(total - 100) > 0.01 ? "text-red-700 dark:text-red-400" : "text-teal-700 dark:text-teal-400")}>
        Total weight: {total}% {Math.abs(total - 100) > 0.01 ? "(must be 100%)" : "✓"}
      </p>
      {rubric.criteria.map((c, i) => (
        <fieldset key={c.id} className="rounded-lg border border-slate-200 p-4 dark:border-slate-800">
          <legend className="px-1 text-xs font-semibold uppercase text-slate-500">
            {c.id} · {c.competency}
          </legend>
          <div className="grid gap-3 sm:grid-cols-4">
            <div className="sm:col-span-3">
              <Field label="Criterion name" htmlFor={`n-${i}`}>
                <input id={`n-${i}`} className={inputClass} value={c.name} onChange={(e) => update(i, { name: e.target.value })} />
              </Field>
            </div>
            <Field label="Weight %" htmlFor={`w-${i}`}>
              <input
                id={`w-${i}`}
                type="number"
                min={1}
                max={100}
                className={inputClass}
                value={c.weight}
                onChange={(e) => update(i, { weight: Number(e.target.value) })}
              />
            </Field>
          </div>
          <div className="mt-3">
            <Field label="Description" htmlFor={`d-${i}`}>
              <textarea id={`d-${i}`} rows={2} className={inputClass} value={c.description} onChange={(e) => update(i, { description: e.target.value })} />
            </Field>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {c.levels.map((lv, li) => (
              <div key={li} className="rounded-md bg-slate-50 p-2 dark:bg-slate-800">
                <div className="flex gap-2">
                  <input
                    aria-label={`Level ${li + 1} score`}
                    type="number"
                    min={0}
                    max={100}
                    className={cx(inputClass, "w-20")}
                    value={lv.score}
                    onChange={(e) => updateLevel(i, li, { score: Number(e.target.value) })}
                  />
                  <input
                    aria-label={`Level ${li + 1} label`}
                    className={inputClass}
                    value={lv.label}
                    onChange={(e) => updateLevel(i, li, { label: e.target.value })}
                  />
                </div>
                <textarea
                  aria-label={`Level ${li + 1} descriptor`}
                  rows={2}
                  className={cx(inputClass, "mt-1")}
                  value={lv.descriptor}
                  onChange={(e) => updateLevel(i, li, { descriptor: e.target.value })}
                />
              </div>
            ))}
          </div>
        </fieldset>
      ))}
      <Field label="Change note" htmlFor="rubric_note">
        <input id="rubric_note" name="change_note" maxLength={500} className={inputClass} placeholder="What changed and why?" />
      </Field>
      <SubmitButton variant="teal">Save rubric as new version</SubmitButton>
    </form>
  );
}

export function DefinitionEditor({ initial }: { initial: unknown }) {
  const [state, action] = useActionState(validateScenarioAction, {} as State);
  return (
    <form action={action} className="space-y-3">
      <Messages state={state} />
      <Field
        label="Scenario definition (JSON)"
        htmlFor="definition"
        hint="Everything is validated on the server: structure, cross-references, conditions and rubric weights."
      >
        <textarea
          id="definition"
          name="definition"
          rows={28}
          spellCheck={false}
          defaultValue={JSON.stringify(initial, null, 2)}
          className={cx(inputClass, "font-mono text-xs")}
        />
      </Field>
      <Field label="Change note" htmlFor="change_note">
        <input id="change_note" name="change_note" maxLength={500} className={inputClass} />
      </Field>
      <div className="flex flex-wrap gap-2">
        <SubmitButton variant="secondary" name="intent" value="validate">
          Validate
        </SubmitButton>
        <SubmitButton name="intent" value="save">
          Save as new version
        </SubmitButton>
      </div>
    </form>
  );
}
