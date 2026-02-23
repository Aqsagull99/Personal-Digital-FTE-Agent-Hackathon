"use client";

import { ThemeToggle } from "@/components/theme-toggle";
import { useOpsStore } from "@/lib/ops-store";
import { useTier } from "@/lib/use-tier";

export function AppHeader(): JSX.Element {
  const wsConnected = useOpsStore((s) => s.wsConnected);
  const { tier } = useTier();
  const userName = process.env.NEXT_PUBLIC_USER_NAME || "Operator";

  return (
    <header className="mb-4 flex items-center justify-between rounded-2xl border border-[var(--line)] bg-[var(--surface-1)] px-4 py-3 shadow-[0_10px_24px_rgba(15,23,42,0.08)]">
      <div>
        <p className="text-xs uppercase tracking-[0.14em] text-[var(--muted)]">AI Operations Console</p>
        <h1 className="text-lg font-semibold text-[var(--text)]">AI Employee Control Center</h1>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => window.dispatchEvent(new Event("open-command-palette"))}
          className="hidden rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-2.5 py-1 text-xs text-[var(--muted)] md:inline-flex"
        >
          Ctrl + K
        </button>
        <span className="hidden rounded-full border border-[var(--line)] px-2.5 py-1 text-xs font-medium text-[var(--muted)] md:inline-flex">
          {userName} • {tier.toUpperCase()}
        </span>
        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${wsConnected ? "bg-[rgba(39,209,154,0.16)] text-[var(--ok)]" : "bg-[rgba(214,69,93,0.14)] text-[var(--bad)]"}`}>
          {wsConnected ? "Running" : "Disconnected"}
        </span>
        <ThemeToggle />
      </div>
    </header>
  );
}
