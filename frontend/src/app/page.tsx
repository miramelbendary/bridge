import Link from "next/link";

const SPECIALIZATIONS = [
  {
    name: "International Trade",
    text: "Handle a delayed shipment, weigh freight costs and negotiate with suppliers and customers.",
  },
  {
    name: "Translation",
    text: "Deliver culturally adapted English–Arabic translations to demanding clients.",
  },
  {
    name: "INFOCOM",
    text: "Manage a media crisis, verify information and respond without amplifying misinformation.",
  },
];

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-16 sm:px-6">
      <p className="text-sm font-semibold tracking-wide text-blue-700 dark:text-blue-400">BRIDGE</p>
      <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-tight text-slate-900 dark:text-slate-50">
        Practise the workplace before you get there.
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-slate-600 dark:text-slate-300">
        BRIDGE places university students in simulated professional workplaces, with colleagues,
        clients and consequences, and gives feedback grounded in what you actually did.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/register"
          className="rounded-md bg-blue-700 px-5 py-2.5 font-medium text-white hover:bg-blue-800"
        >
          Create a student account
        </Link>
        <Link
          href="/login"
          className="rounded-md border border-slate-300 px-5 py-2.5 font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          Sign in
        </Link>
      </div>

      <section className="mt-16 grid gap-4 sm:grid-cols-3" aria-label="Specializations">
        {SPECIALIZATIONS.map((s) => (
          <div
            key={s.name}
            className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
          >
            <h2 className="font-medium text-teal-800 dark:text-teal-300">{s.name}</h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{s.text}</p>
          </div>
        ))}
      </section>

      <p className="mt-16 text-xs text-slate-500 dark:text-slate-500">
        Development build. BRIDGE is a formative learning tool; simulations and organisations are
        fictional.
      </p>
    </main>
  );
}
