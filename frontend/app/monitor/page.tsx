"use client";

import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchSystemMonitor } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { formatDateTime, healthTone } from "@/lib/utils";

export default function MonitorPage(): JSX.Element {
  const monitor = useLiveQuery("system-monitor", fetchSystemMonitor, { refreshInterval: 5000 });
  const data = monitor.data;

  return (
    <AppShell>
      <Panel
        title="Live System Monitor"
        subtitle="Claude loop, watcher processes, execution health"
        action={<button className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm text-white" onClick={() => void monitor.refresh()}>{monitor.loading ? "Loading..." : "Refresh"}</button>}
      >
        {monitor.error ? <p className="mb-3 text-xs text-[var(--bad)]">{monitor.error}</p> : null}
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Claude Status</p>
            <p className="mt-1 text-xl font-semibold text-[var(--text)]">{data?.claudeStatus ?? "unknown"}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Last Execution</p>
            <p className="mt-1 text-sm font-semibold text-[var(--text)]">{data?.lastExecutionTime ? formatDateTime(data.lastExecutionTime) : "n/a"}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Loop Iterations</p>
            <p className="mt-1 text-xl font-semibold text-[var(--text)]">{data?.loopIterationCount ?? 0}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Error Alerts</p>
            <p className="mt-1 text-xl font-semibold text-[var(--bad)]">{data?.errorAlerts.length ?? 0}</p>
          </div>
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Watcher Status" subtitle="Running/stopped process status">
          <div className="space-y-2">
            {(data?.watcherStatus ?? []).map((watcher) => (
              <div key={watcher.name} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-[var(--text)]">{watcher.name}</p>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${watcher.running ? "bg-[rgba(39,209,154,0.2)] text-[var(--ok)]" : "bg-[rgba(255,109,122,0.2)] text-[var(--bad)]"}`}>{watcher.running ? "running" : "stopped"}</span>
                </div>
                <p className="mt-1 text-xs text-[var(--muted)]">PID: {watcher.pid ?? "-"}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Error Alerts" subtitle="Recent failed events">
          <div className="space-y-2">
            {(data?.errorAlerts ?? []).map((err) => (
              <div key={err.id} className="rounded-xl border border-[rgba(255,109,122,0.35)] bg-[rgba(255,109,122,0.08)] p-3">
                <p className="text-sm font-semibold text-[var(--bad)]">{err.actionType}</p>
                <p className="text-xs text-[var(--muted)]">{err.actor} • {formatDateTime(err.timestamp)}</p>
                <pre className="mt-2 overflow-auto rounded-lg bg-[rgba(7,11,18,0.9)] p-2 text-xs text-[var(--text)]">{JSON.stringify(err.raw, null, 2)}</pre>
              </div>
            ))}
            {(data?.errorAlerts.length ?? 0) === 0 && !monitor.loading ? <p className="text-sm text-[var(--muted)]">No recent errors.</p> : null}
          </div>
        </Panel>
      </div>

      <Panel title="Watcher Health" subtitle="Heartbeat status indicators">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(data?.watcherHealth ?? []).map((item) => (
            <div key={item.name} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
              <p className="text-sm font-medium text-[var(--text)]">{item.name}</p>
              <p className="text-xs text-[var(--muted)]">Last seen: {item.lastSeen}</p>
              <span className={`mt-2 inline-block rounded-full px-2 py-0.5 text-xs ${healthTone(item.status)}`}>{item.status}</span>
            </div>
          ))}
        </div>
      </Panel>
    </AppShell>
  );
}
