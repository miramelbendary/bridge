"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cx } from "./ui";

export type NavItem = { href: string; label: string };

export function NavLinks({ items }: { items: NavItem[] }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="-mx-1 flex gap-1 overflow-x-auto">
      {items.map((item) => {
        const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cx(
              "whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium",
              active
                ? "bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-200"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
