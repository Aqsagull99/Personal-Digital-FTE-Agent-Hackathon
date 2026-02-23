"use client";

import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchCompliancePanel } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { formatDateTime } from "@/lib/utils";

export default function CompliancePage(): JSX.Element {
  const compliance = useLiveQuery("compliance-panel", fetchCompliancePanel, { refreshInterval: 9000 });
  const data = compliance.data;

  return (
    <AppShell>
      <Panel title="Audit & Compliance Panel" subtitle="Action logs, approvals, recovery, retries">
        {compliance.error ? <p className="mb-3 text-xs text-[var(--bad)]">{compliance.error}</p> : null}
        <div className="grid gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3"><p className="text-xs text-[var(--muted)]">Action Logs</p><p className="mt-1 text-2xl font-semibold text-[var(--text)]">{data?.actionLogs.length ?? 0}</p></div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3"><p className="text-xs text-[var(--muted)]">Approval History</p><p className="mt-1 text-2xl font-semibold text-[var(--text)]">{data?.approvalHistory.length ?? 0}</p></div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3"><p className="text-xs text-[var(--muted)]">Recovery Logs</p><p className="mt-1 text-2xl font-semibold text-[var(--text)]">{data?.failureRecoveryLogs.length ?? 0}</p></div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3"><p className="text-xs text-[var(--muted)]">Retry Attempts</p><p className="mt-1 text-2xl font-semibold text-[var(--warn)]">{data?.retryAttempts ?? 0}</p></div>
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Failure Recovery Logs" subtitle="Recovered/failed execution traces">
          <div className="space-y-2">
            {(data?.failureRecoveryLogs ?? []).slice(0, 40).map((item) => (
              <div key={item.id} className="rounded-xl border border-[rgba(255,109,122,0.3)] bg-[rgba(255,109,122,0.08)] p-3">
                <p className="text-sm font-semibold text-[var(--text)]">{item.actionType}</p>
                <p className="text-xs text-[var(--muted)]">{item.actor} • {formatDateTime(item.timestamp)}</p>
                <pre className="mt-2 overflow-auto rounded-lg bg-[rgba(7,11,18,0.95)] p-2 text-xs text-[var(--text)]">{JSON.stringify(item.raw, null, 2)}</pre>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Approval History" subtitle="Compliance trail of approval actions">
          <div className="space-y-2">
            {(data?.approvalHistory ?? []).slice(0, 40).map((item) => (
              <div key={item.id} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
                <p className="text-sm font-semibold text-[var(--text)]">{item.actionType}</p>
                <p className="text-xs text-[var(--muted)]">{item.actor} • {formatDateTime(item.timestamp)}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}
