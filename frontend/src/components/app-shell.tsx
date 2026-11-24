import Link from "next/link";
import type { ReactNode } from "react";

import { logoutAction } from "@/app/actions/auth";
import { getCurrentUser } from "@/lib/auth";

import { NavLinks, type NavItem } from "./nav-links";
import { Badge } from "./ui";

const ROLE_LABEL = { student: "Student", professor: "Professor", admin: "Administrator" } as const;

export async function AppShell({ children }: { children: ReactNode }) {
  const user = await getCurrentUser();
  const items: NavItem[] = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/scenarios", label: "Scenarios" },
    { href: "/history", label: "History" },
    { href: "/profile", label: "Competencies" },
  ];
  if (user.role === "professor" || user.role === "admin") {
    items.push({ href: "/teach", label: "Teaching" });
  }
  if (user.role === "admin") items.push({ href: "/admin", label: "Admin" });

  return (
    <>
      <header className="border-b border-slate-200 bg-white print:hidden dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
          <Link href="/dashboard" className="text-sm font-bold tracking-wider text-blue-700 dark:text-blue-400">
            BRIDGE
          </Link>
          <div className="order-3 w-full sm:order-none sm:w-auto sm:flex-1">
            <NavLinks items={items} />
          </div>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden text-sm text-slate-600 md:inline dark:text-slate-300">
              {user.profile?.display_name ?? user.email}
            </span>
            <Badge tone="teal">{ROLE_LABEL[user.role]}</Badge>
            <form action={logoutAction}>
              <button
                type="submit"
                className="rounded-md px-2 py-1 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                Sign out
              </button>
            </form>
          </div>
        </div>
      </header>
      <div className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</div>
    </>
  );
}
