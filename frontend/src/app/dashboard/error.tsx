"use client";

export default function DashboardError({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6">
      <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950">
        <h1 className="text-lg font-semibold text-red-900 dark:text-red-100">
          We couldn&apos;t load your dashboard
        </h1>
        <p className="mt-1 text-sm text-red-800 dark:text-red-200">
          The BRIDGE service may be temporarily unavailable. Your data has not been lost.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-4 rounded-md bg-red-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-800"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
