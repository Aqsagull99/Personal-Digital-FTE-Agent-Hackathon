"use client";

import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchSystemHealth } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { useOpsStore } from "@/lib/ops-store";

export default function HealthPage(): JSX.Element {
  const health = useLiveQuery("system-health", fetchSystemHealth, { refreshInterval: 4000 });
  const data = health.data;

  const wsConnected = useOpsStore((s) => s.wsConnected);
  const liveHealth = useOpsStore((s) => s.liveHealth);

  const effective = liveHealth ?? data;

  return (
    <AppShell>
      <Panel title="System Health" subtitle="Watchdog, CPU, process state, queue metrics">
        {health.error ? <p className="mb-3 text-xs text-[var(--bad)]">{health.error}</p> : null}
        <div className="grid gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">WebSocket</p>
            <p className="mt-1 text-xl font-semibold text-[var(--text)]">{wsConnected ? "connected" : "disconnected"}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Watchdog</p>
            <p className="mt-1 text-xl font-semibold text-[var(--text)]">{effective?.watchdogStatus ?? "n/a"}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">CPU Usage</p>
            <p className="mt-1 text-xl font-semibold text-[var(--text)]">{(effective?.cpuLoadPercent ?? 0).toFixed(1)}%</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Queue Size</p>
            <p className="mt-1 text-xl font-semibold text-[var(--text)]">{Object.values(effective?.queueSize ?? {}).reduce((a, b) => a + b, 0)}</p>
          </div>
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Process Status" subtitle="Watcher process runtime state">
          <div className="space-y-2">
            {(effective?.processStatus ?? []).map((proc) => (
              <div key={proc.name} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-[var(--text)]">{proc.name}</p>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${proc.running ? "bg-[rgba(39,209,154,0.2)] text-[var(--ok)]" : "bg-[rgba(255,109,122,0.2)] text-[var(--bad)]"}`}>{proc.running ? "running" : "stopped"}</span>
                </div>
                <p className="text-xs text-[var(--muted)]">PID: {proc.pid ?? "-"}</p>
                <p className="text-xs text-[var(--muted)]">Log: {proc.logFile}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Queue Breakdown" subtitle="Folder queue depth mapping">
          <div className="space-y-2">
            {Object.entries(effective?.queueSize ?? {}).map(([key, value]) => (
              <div key={key} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
                <p className="text-sm font-semibold text-[var(--text)]">{key}</p>
                <p className="text-xs text-[var(--muted)]">{value}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}
