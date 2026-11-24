"use client";

import { useMemo, useState, useTransition } from "react";

import {
  finishStep,
  hintStep,
  performActionStep,
  sendMessageStep,
  submitWorkStep,
} from "@/app/actions/sim";
import { Markdown } from "@/components/markdown";
import { Alert, Badge, Button, Card, Meter, cx, inputClass } from "@/components/ui";
import type { SessionView } from "@/lib/api";
import { simTime, titleCase } from "@/lib/format";

type Tab = "inbox" | "messages" | "documents" | "deliverables" | "decisions";

const TABS: { id: Tab; label: string }[] = [
  { id: "inbox", label: "Inbox" },
  { id: "messages", label: "Messages" },
  { id: "documents", label: "Documents" },
  { id: "deliverables", label: "Deliverables" },
  { id: "decisions", label: "Decisions" },
];

const REPLY_LABELS: Record<string, { text: string; tone: "slate" | "amber" | "blue" }> = {
  mock: { text: "Offline simulated reply", tone: "slate" },
  scripted: { text: "Scripted response", tone: "blue" },
  fallback: { text: "AI unavailable — scripted reply", tone: "amber" },
  limit: { text: "AI limit reached — scripted reply", tone: "amber" },
};

const newKey = () => crypto.randomUUID();

function words(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

export function Workplace({ initial }: { initial: SessionView }) {
  const [view, setView] = useState(initial);
  const [tab, setTab] = useState<Tab>("inbox");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [activeChar, setActiveChar] = useState(initial.characters[0]?.id ?? "");
  const [activeDoc, setActiveDoc] = useState(initial.documents[0]?.id ?? "");
  const [message, setMessage] = useState("");
  const [justifications, setJustifications] = useState<Record<string, string>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>(() =>
    Object.fromEntries(initial.submissions.map((s) => [s.id, s.current?.text ?? s.template ?? ""])),
  );

  const readOnly = Boolean(view.read_only) || view.finished || view.status !== "active";
  const chars = useMemo(() => Object.fromEntries(view.characters.map((c) => [c.id, c])), [view.characters]);
  const remaining = Math.max(0, view.time_limit - view.clock);

  function run<T extends { view: SessionView; result: Record<string, unknown> }>(
    fn: () => Promise<{ ok: true; data: T } | { ok: false; error: string }>,
    onOk?: (data: T) => void,
  ) {
    setError(null);
    setNotice(null);
    startTransition(async () => {
      const result = await fn();
      if (!result.ok) {
        setError(result.error);
        return;
      }
      setView(result.data.view);
      onOk?.(result.data);
    });
  }

  function doAction(actionId: string) {
    run(
      () => performActionStep(view.session_id, actionId, justifications[actionId] ?? "", newKey()),
      () => setJustifications((j) => ({ ...j, [actionId]: "" })),
    );
  }

  function send() {
    const text = message.trim();
    if (!text) return;
    run(
      () => sendMessageStep(view.session_id, activeChar, text, newKey()),
      (data) => {
        setMessage("");
        const performed = data.result.performed_action as string | null;
        if (performed) setNotice("Your message was recognised as a workplace action — see the activity feed.");
      },
    );
  }

  function submit(submissionId: string) {
    run(() => submitWorkStep(view.session_id, submissionId, drafts[submissionId] ?? "", newKey()), () =>
      setNotice("Saved. You can revise it until you finish the simulation."),
    );
  }

  function hint() {
    run(
      () => hintStep(view.session_id, newKey()),
      (data) => setNotice(`Hint: ${String(data.result.hint ?? "")}`),
    );
  }

  function finish() {
    const open = view.tasks.filter((t) => t.required && t.status === "open").length;
    const warning = open ? `${open} required task(s) are still open. ` : "";
    if (!window.confirm(`${warning}Finish the simulation and generate your assessment? This cannot be undone.`)) return;
    setError(null);
    startTransition(async () => {
      const result = await finishStep(view.session_id, newKey());
      if (result && !result.ok) setError(result.error);
    });
  }

  const conversation = view.conversations[activeChar] ?? [];
  const doc = view.documents.find((d) => d.id === activeDoc) ?? view.documents[0];

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card className="!p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">{view.title}</h1>
            <p className="text-sm text-slate-500">
              {view.context.student_role} · {view.context.organization}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge tone={view.mode === "training" ? "teal" : "blue"}>{titleCase(view.mode)} mode</Badge>
              <Badge>{titleCase(view.difficulty)}</Badge>
              {view.read_only ? <Badge tone="amber">Read-only view</Badge> : null}
              {view.finished ? <Badge tone="slate">Completed</Badge> : null}
              {view.assessment_id ? (
                <a href={`/sessions/${view.session_id}/report`} className="text-sm font-medium text-blue-700 hover:underline dark:text-blue-300">
                  View report →
                </a>
              ) : null}
            </div>
          </div>
          <div className="min-w-[220px] flex-1 sm:flex-none">
            <p className="text-sm">
              <span className="font-semibold tabular-nums">{simTime(view.clock)}</span>
              <span className="text-slate-500"> · {remaining} simulated min left</span>
            </p>
            <div className="mt-1">
              <Meter value={remaining} min={0} max={view.time_limit} label="Simulated time remaining" />
            </div>
            {!readOnly ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {view.hints_available ? (
                  <Button variant="secondary" onClick={hint} disabled={pending}>
                    Get a hint
                  </Button>
                ) : null}
                <Button variant="teal" onClick={finish} disabled={pending}>
                  Finish &amp; get feedback
                </Button>
              </div>
            ) : null}
          </div>
        </div>
        {view.time_up && !view.finished ? (
          <div className="mt-3">
            <Alert tone="warning">Simulated working time is over. Save any final deliverables and finish.</Alert>
          </div>
        ) : null}
      </Card>

      <div aria-live="polite" className="space-y-2">
        {error ? <Alert tone="error">{error}</Alert> : null}
        {notice ? <Alert tone="success">{notice}</Alert> : null}
        {pending ? <p className="text-sm text-slate-500">Working…</p> : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        {/* Left: tasks + status */}
        <aside className="space-y-4 lg:col-span-3">
          <Card className="!p-4">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Tasks</h2>
            <ul className="space-y-2">
              {view.tasks.map((t) => (
                <li key={t.id} className="flex gap-2 text-sm">
                  <span
                    aria-hidden="true"
                    className={cx(
                      "mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[10px]",
                      t.status === "done" ? "border-teal-600 bg-teal-600 text-white" : "border-slate-400",
                    )}
                  >
                    {t.status === "done" ? "✓" : ""}
                  </span>
                  <span>
                    <span className={cx("font-medium", t.status === "done" && "text-slate-500 line-through")}>{t.title}</span>
                    <span className="sr-only">{t.status === "done" ? " (done)" : " (open)"}</span>
                    {!t.required ? <span className="text-xs text-slate-500"> (optional)</span> : null}
                    <span className="block text-xs text-slate-500">{t.description}</span>
                  </span>
                </li>
              ))}
            </ul>
          </Card>
          <Card className="!p-4">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Situation</h2>
            <ul className="space-y-3">
              {view.variables.map((v) => (
                <li key={v.id} title={v.description}>
                  <div className="flex justify-between text-sm">
                    <span>{v.label}</span>
                    <span className="font-semibold tabular-nums">
                      {v.unit === "EUR" || v.unit === "USD" ? `${v.value.toLocaleString("en-GB")} ${v.unit}` : `${v.value}${v.unit === "%" ? "%" : ` ${v.unit}`}`}
                    </span>
                  </div>
                  {v.max !== null ? <Meter value={v.value} min={v.min} max={v.max} label={v.label} /> : null}
                </li>
              ))}
            </ul>
          </Card>
        </aside>

        {/* Centre: tabs */}
        <section className="lg:col-span-6">
          <div role="tablist" aria-label="Workplace" className="mb-3 flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-slate-800">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                aria-controls={`panel-${t.id}`}
                id={`tab-${t.id}`}
                onClick={() => setTab(t.id)}
                className={cx(
                  "whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium",
                  tab === t.id
                    ? "border-blue-700 text-blue-800 dark:text-blue-300"
                    : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200",
                )}
              >
                {t.label}
                {t.id === "inbox" ? ` (${view.inbox.length})` : ""}
                {t.id === "decisions" && !readOnly ? ` (${view.actions.length})` : ""}
              </button>
            ))}
          </div>

          <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
            {tab === "inbox" ? (
              <ul className="space-y-3">
                {view.inbox.length === 0 ? <p className="text-sm text-slate-500">No messages.</p> : null}
                {view.inbox.map((m) => (
                  <li key={m.id}>
                    <Card className="!p-4">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="font-medium">{m.subject}</p>
                        <span className="text-xs text-slate-500 tabular-nums">{simTime(m.minute)}</span>
                      </div>
                      <p className="text-xs text-slate-500">
                        From {chars[m.sender]?.name ?? m.sender}, {chars[m.sender]?.role}
                      </p>
                      <div className="mt-2">
                        <Markdown>{m.body}</Markdown>
                      </div>
                      {!readOnly && chars[m.sender] ? (
                        <Button
                          variant="ghost"
                          className="mt-2 !px-0 text-blue-700 dark:text-blue-300"
                          onClick={() => {
                            setActiveChar(m.sender);
                            setTab("messages");
                          }}
                        >
                          Reply to {chars[m.sender]?.name.split(" ")[0]} →
                        </Button>
                      ) : null}
                    </Card>
                  </li>
                ))}
              </ul>
            ) : null}

            {tab === "messages" ? (
              <div className="grid gap-3 sm:grid-cols-3">
                <ul className="space-y-1 sm:col-span-1" aria-label="People">
                  {view.characters.map((c) => (
                    <li key={c.id}>
                      <button
                        onClick={() => setActiveChar(c.id)}
                        aria-pressed={activeChar === c.id}
                        className={cx(
                          "w-full rounded-md px-3 py-2 text-left text-sm",
                          activeChar === c.id ? "bg-blue-50 dark:bg-blue-950" : "hover:bg-slate-100 dark:hover:bg-slate-800",
                        )}
                      >
                        <span className="block font-medium">{c.name}</span>
                        <span className="block text-xs text-slate-500">
                          {c.role} · {c.organization.split(" (")[0]}
                        </span>
                        <span className="text-xs text-slate-500">Mood: {c.mood}</span>
                      </button>
                    </li>
                  ))}
                </ul>
                <Card className="!p-4 sm:col-span-2">
                  <ol className="max-h-[420px] space-y-3 overflow-y-auto" aria-label="Conversation" aria-live="polite">
                    {conversation.length === 0 ? (
                      <li className="text-sm text-slate-500">No messages yet. Write to start the conversation.</li>
                    ) : null}
                    {conversation.map((entry) => (
                      <li key={entry.seq} className={cx("flex", entry.role === "student" ? "justify-end" : "justify-start")}>
                        <div
                          className={cx(
                            "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                            entry.role === "student"
                              ? "bg-blue-700 text-white"
                              : "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-100",
                          )}
                          dir="auto"
                        >
                          <p className="whitespace-pre-wrap">{entry.text}</p>
                          <p className={cx("mt-1 text-[10px]", entry.role === "student" ? "text-blue-100" : "text-slate-500")}>
                            {simTime(entry.minute)}
                            {entry.label && REPLY_LABELS[entry.label] ? ` · ${REPLY_LABELS[entry.label].text}` : ""}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ol>
                  {!readOnly ? (
                    <div className="mt-3 space-y-2">
                      <label htmlFor="chat" className="sr-only">
                        Message to {chars[activeChar]?.name}
                      </label>
                      <textarea
                        id="chat"
                        dir="auto"
                        rows={3}
                        maxLength={2000}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send();
                        }}
                        placeholder={`Write to ${chars[activeChar]?.name ?? ""}… (Ctrl+Enter to send)`}
                        className={inputClass}
                      />
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs text-slate-500">
                          Characters are simulated. Your messages can count as workplace actions.
                        </p>
                        <Button onClick={send} disabled={pending || !message.trim()}>
                          Send
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </Card>
              </div>
            ) : null}

            {tab === "documents" ? (
              <div className="grid gap-3 sm:grid-cols-3">
                <ul className="space-y-1" aria-label="Documents">
                  {view.documents.map((d) => (
                    <li key={d.id}>
                      <button
                        onClick={() => setActiveDoc(d.id)}
                        aria-pressed={doc?.id === d.id}
                        className={cx(
                          "w-full rounded-md px-3 py-2 text-left text-sm",
                          doc?.id === d.id ? "bg-blue-50 dark:bg-blue-950" : "hover:bg-slate-100 dark:hover:bg-slate-800",
                        )}
                      >
                        {d.title}
                        <span className="block text-xs text-slate-500">{titleCase(d.kind)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
                <Card className="!p-4 sm:col-span-2">
                  {doc ? (
                    <>
                      <h3 className="mb-3 font-semibold">{doc.title}</h3>
                      <div className="overflow-x-auto">
                        <Markdown dir={doc.direction}>{doc.body}</Markdown>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-slate-500">No documents.</p>
                  )}
                </Card>
              </div>
            ) : null}

            {tab === "deliverables" ? (
              <div className="space-y-4">
                {view.submissions.length === 0 ? <p className="text-sm text-slate-500">No written deliverables in this scenario.</p> : null}
                {view.submissions.map((s) => {
                  const draft = drafts[s.id] ?? "";
                  const count = words(draft);
                  return (
                    <Card key={s.id} className="!p-4">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h3 className="font-semibold">{s.title}</h3>
                        {s.current ? <Badge tone="teal">Saved · revision {s.current.revision}</Badge> : <Badge>Not submitted</Badge>}
                      </div>
                      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{s.prompt}</p>
                      <label htmlFor={`sub-${s.id}`} className="sr-only">
                        {s.title}
                      </label>
                      <textarea
                        id={`sub-${s.id}`}
                        dir={s.direction}
                        lang={s.language}
                        rows={10}
                        maxLength={20000}
                        readOnly={readOnly}
                        value={draft}
                        onChange={(e) => setDrafts((d) => ({ ...d, [s.id]: e.target.value }))}
                        className={cx(inputClass, "mt-3 font-[inherit] leading-relaxed", s.direction === "rtl" && "text-right")}
                      />
                      <div className="mt-2 flex items-center justify-between gap-2">
                        <p className={cx("text-xs", count < s.min_words ? "text-amber-700 dark:text-amber-400" : "text-slate-500")}>
                          {count} words{s.min_words ? ` · at least ${s.min_words} expected` : ""}
                        </p>
                        {!readOnly ? (
                          <Button onClick={() => submit(s.id)} disabled={pending || !draft.trim()}>
                            {s.current ? "Save revision" : "Submit"}
                          </Button>
                        ) : null}
                      </div>
                    </Card>
                  );
                })}
              </div>
            ) : null}

            {tab === "decisions" ? (
              <div className="space-y-3">
                {readOnly ? <p className="text-sm text-slate-500">Decisions are closed for this session.</p> : null}
                {!readOnly && view.actions.length === 0 ? (
                  <p className="text-sm text-slate-500">No decisions are available right now. Investigate, communicate, or write your deliverables.</p>
                ) : null}
                {!readOnly &&
                  view.actions.map((a) => (
                    <Card key={a.id} className="!p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <p className="font-medium">{a.label}</p>
                          <p className="text-sm text-slate-600 dark:text-slate-400">{a.description}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {titleCase(a.category)} · takes about {a.duration_minutes} min
                            {a.via_character ? ` · involves ${chars[a.via_character]?.name ?? a.via_character}` : ""}
                          </p>
                        </div>
                      </div>
                      {a.requires_justification ? (
                        <div className="mt-3">
                          <label htmlFor={`j-${a.id}`} className="text-xs font-medium text-slate-700 dark:text-slate-300">
                            Your reasoning (required)
                          </label>
                          <textarea
                            id={`j-${a.id}`}
                            rows={2}
                            maxLength={2000}
                            value={justifications[a.id] ?? ""}
                            onChange={(e) => setJustifications((j) => ({ ...j, [a.id]: e.target.value }))}
                            className={cx(inputClass, "mt-1")}
                            placeholder="Why is this the right decision? Consider costs, risks and stakeholders."
                          />
                        </div>
                      ) : null}
                      <div className="mt-3 flex justify-end">
                        <Button
                          variant="secondary"
                          onClick={() => doAction(a.id)}
                          disabled={pending || (a.requires_justification && (justifications[a.id] ?? "").trim().length < 15)}
                        >
                          Do this
                        </Button>
                      </div>
                    </Card>
                  ))}
              </div>
            ) : null}
          </div>
        </section>

        {/* Right: activity */}
        <aside className="space-y-4 lg:col-span-3">
          {view.mode === "training" && view.feedback.length ? (
            <Card className="!p-4 border-teal-200 dark:border-teal-900">
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-400">Coaching</h2>
              <ul className="space-y-2 text-sm">
                {view.feedback.slice(0, 6).map((f, i) => (
                  <li key={`${f.minute}-${i}`}>{f.text}</li>
                ))}
              </ul>
            </Card>
          ) : null}
          <Card className="!p-4">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Activity</h2>
            {view.log.length === 0 ? <p className="text-sm text-slate-500">Nothing has happened yet.</p> : null}
            <ol className="space-y-2 text-sm">
              {view.log.slice(0, 15).map((entry, i) => (
                <li key={`${entry.minute}-${i}`} className="border-l-2 border-slate-200 pl-2 dark:border-slate-700">
                  <span className="text-xs text-slate-500 tabular-nums">{simTime(entry.minute)}</span>
                  <p className={cx(entry.kind === "event" && "font-medium text-amber-800 dark:text-amber-300")}>{entry.text}</p>
                </li>
              ))}
            </ol>
          </Card>
          <Card className="!p-4">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Briefing</h2>
            <p className="text-sm text-slate-700 dark:text-slate-300">{view.context.briefing}</p>
            <p className="mt-2 text-xs text-slate-500">{view.fictional_notice}</p>
          </Card>
        </aside>
      </div>
    </div>
  );
}
