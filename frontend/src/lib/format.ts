export function simTime(minute: number): string {
  // Simulated working day starts at 09:00.
  const total = 9 * 60 + minute;
  const h = Math.floor(total / 60) % 24;
  const m = total % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" });
}

export function score(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : value.toFixed(0);
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function scoreTone(value: number | null | undefined): string {
  if (value === null || value === undefined) return "text-slate-500";
  if (value >= 75) return "text-teal-700 dark:text-teal-400";
  if (value >= 55) return "text-amber-700 dark:text-amber-400";
  return "text-red-700 dark:text-red-400";
}
