"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { setRoleCookie } from "@/lib/auth-client";
import type { UserRole } from "@/lib/rbac";

const roles: Array<{ role: UserRole; label: string; desc: string }> = [
  { role: "admin", label: "Admin", desc: "Full control including watcher/process operations and manual override." },
  { role: "finance", label: "Finance", desc: "Financial approvals and accounting-focused operations." },
  { role: "ops_reviewer", label: "Ops Reviewer", desc: "Operational approval decisions and execution review." },
  { role: "observer", label: "Observer", desc: "Read-only executive visibility." }
];

export default function AuthRolePage(): JSX.Element {
  const [selected, setSelected] = useState<UserRole>("observer");
  const router = useRouter();
  const search = useSearchParams();

  function applyRole(): void {
    setRoleCookie(selected);
    const next = search.get("next") || "/";
    router.push(next);
  }

  return (
    <AppShell>
      <Panel title="Access Role" subtitle="Select role profile for this console session">
        <div className="space-y-2">
          {roles.map((item) => (
            <button key={item.role} onClick={() => setSelected(item.role)} className={`w-full rounded-xl border p-3 text-left ${selected === item.role ? "border-[var(--accent)] bg-[rgba(79,124,255,0.12)]" : "border-[var(--line)] bg-[rgba(11,18,32,0.68)]"}`}>
              <p className="text-sm font-semibold text-[var(--text)]">{item.label}</p>
              <p className="text-xs text-[var(--muted)]">{item.desc}</p>
            </button>
          ))}
        </div>
        <button className="mt-4 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white" onClick={applyRole}>
          Continue as {selected}
        </button>
      </Panel>
    </AppShell>
  );
}
