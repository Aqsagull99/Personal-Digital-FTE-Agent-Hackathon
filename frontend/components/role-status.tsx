"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { getCurrentRole } from "@/lib/auth-client";

export function RoleStatus(): JSX.Element {
  const role = getCurrentRole();
  const pathname = usePathname();

  return (
    <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3 shadow-sm">
      <p className="text-xs text-[var(--muted)]">Role</p>
      <p className="text-sm font-semibold text-[var(--text)]">{role}</p>
      <Link href={`/auth?next=${encodeURIComponent(pathname || "/")}`} className="mt-2 inline-block text-xs text-[var(--accent)]">
        Switch role
      </Link>
    </div>
  );
}
