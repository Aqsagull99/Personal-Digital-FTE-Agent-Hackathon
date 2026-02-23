"use client";

import { useMemo, useState } from "react";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchLogs } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { formatDateTime } from "@/lib/utils";

type Channel = "email" | "payment" | "social" | "system" | "file" | "other";

export default function LogsPage(): JSX.Element {
  const [channel, setChannel] = useState<Channel | "">("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  const key = useMemo(() => `logs-${channel}-${dateFrom}-${dateTo}`, [channel, dateFrom, dateTo]);
  const logsQuery = useLiveQuery(key, () => fetchLogs({ channel: channel || undefined, dateFrom: dateFrom || undefined, dateTo: dateTo || undefined, limit: 500 }), { refreshInterval: 7000 });
  const logs = logsQuery.data ?? [];

  return (
    <AppShell>
      <Panel
        title="Activity Logs"
        subtitle="Filter by action type and date"
        action={<button className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm text-white" onClick={() => void logsQuery.refresh()}>{logsQuery.loading ? "Loading..." : "Refresh"}</button>}
      >
        <div className="mb-4 grid gap-3 md:grid-cols-3">
          <label className="text-xs text-[var(--muted)]">
            Action Type
            <select value={channel} onChange={(e) => setChannel(e.target.value as Channel | "")} className="mt-1 w-full rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-2 py-2 text-sm text-[var(--text)]">
              <option value="">All</option>
              <option value="email">Email</option>
              <option value="payment">Payment</option>
              <option value="social">Social</option>
              <option value="system">System</option>
              <option value="file">File</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className="text-xs text-[var(--muted)]">
            Date From
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="mt-1 w-full rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-2 py-2 text-sm text-[var(--text)]" />
          </label>
          <label className="text-xs text-[var(--muted)]">
            Date To
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="mt-1 w-full rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-2 py-2 text-sm text-[var(--text)]" />
          </label>
        </div>

        {logsQuery.error ? <p className="mb-3 text-xs text-[var(--bad)]">{logsQuery.error}</p> : null}

        <div className="space-y-3">
          {logs.map((record) => (
            <article key={record.id} className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-[var(--text)]">{record.actionType}</p>
                <span className={`rounded-full px-2 py-0.5 text-xs ${record.status === "success" ? "bg-[rgba(17,154,111,0.18)] text-[var(--ok)]" : "bg-[rgba(214,69,93,0.16)] text-[var(--bad)]"}`}>{record.status}</span>
              </div>
              <p className="mt-1 text-xs text-[var(--muted)]">Channel: {record.channel} • Actor: {record.actor}</p>
              <p className="mt-1 text-xs text-[var(--muted)]">{formatDateTime(record.timestamp)}</p>
              <div className="mt-2 overflow-auto rounded-lg border border-[var(--line)] bg-[var(--surface-3)] p-3">
                <pre className="max-h-80 overflow-auto font-mono text-xs leading-relaxed text-[var(--text)]">{JSON.stringify(record.raw, null, 2)}</pre>
              </div>
            </article>
          ))}
          {logs.length === 0 && !logsQuery.loading ? <p className="text-sm text-[var(--muted)]">No logs found for selected filters.</p> : null}
        </div>
      </Panel>
    </AppShell>
  );
}
