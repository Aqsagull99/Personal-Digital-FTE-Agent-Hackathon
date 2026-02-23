"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";

export default function UnauthorizedPage(): JSX.Element {
  const search = useSearchParams();
  const from = search.get("from") || "unknown route";

  return (
    <AppShell>
      <Panel title="Unauthorized" subtitle="Your role does not allow this route.">
        <p className="text-sm text-[var(--muted)]">Blocked route: {from}</p>
        <div className="mt-4 flex gap-2">
          <Link href="/" className="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm text-white">Back to Dashboard</Link>
          <Link href={`/auth?next=${encodeURIComponent(from)}`} className="rounded-lg bg-[rgba(79,124,255,0.2)] px-3 py-2 text-sm text-white">Switch Role</Link>
        </div>
      </Panel>
    </AppShell>
  );
}
