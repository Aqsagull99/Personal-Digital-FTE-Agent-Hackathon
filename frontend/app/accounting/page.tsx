"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchAccountingSummary } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { formatDateTime } from "@/lib/utils";

export default function AccountingPage(): JSX.Element {
  const accounting = useLiveQuery("accounting-panel", fetchAccountingSummary, { refreshInterval: 9000 });
  const data = accounting.data;

  return (
    <AppShell>
      <Panel title="Accounting Panel" subtitle="Revenue, subscriptions, flagged costs, ERP sync">
        {accounting.error ? <p className="mb-3 text-xs text-[var(--bad)]">{accounting.error}</p> : null}
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Monthly Revenue</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--text)]">${(data?.currentMonthRevenue ?? 0).toLocaleString()}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Subscription Analysis</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--text)]">${(data?.subscriptionRevenue ?? 0).toLocaleString()}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">ERP Sync Status</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--text)]">{data?.erpSyncStatus ?? "n/a"}</p>
          </div>
        </div>
      </Panel>

      <Panel title="Revenue by Month" subtitle="Accounting trend overview">
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data?.monthlyRevenue ?? []}>
              <CartesianGrid stroke="#253554" strokeDasharray="3 3" />
              <XAxis dataKey="date" stroke="#8fa3c7" />
              <YAxis stroke="#8fa3c7" />
              <Tooltip contentStyle={{ background: "#121c30", border: "1px solid #253554" }} formatter={(v: number) => [`$${Number(v).toLocaleString()}`, "Revenue"]} />
              <Bar dataKey="value" fill="#4f7cff" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <Panel title="Flagged Costs" subtitle="Anomaly and risk-tracked financial events">
        <div className="space-y-2">
          {(data?.flaggedCosts ?? []).map((row) => (
            <div key={row.id} className="rounded-xl border border-[rgba(241,180,89,0.35)] bg-[rgba(241,180,89,0.08)] p-3">
              <p className="text-sm font-semibold text-[var(--text)]">{row.actionType}</p>
              <p className="text-xs text-[var(--muted)]">{row.actor} • {formatDateTime(row.timestamp)}</p>
              <pre className="mt-2 overflow-auto rounded-lg bg-[rgba(7,11,18,0.95)] p-2 text-xs text-[var(--text)]">{JSON.stringify(row.raw, null, 2)}</pre>
            </div>
          ))}
          {(data?.flaggedCosts.length ?? 0) === 0 && !accounting.loading ? <p className="text-sm text-[var(--muted)]">No flagged costs detected.</p> : null}
        </div>
      </Panel>
    </AppShell>
  );
}
