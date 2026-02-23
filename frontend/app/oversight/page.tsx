"use client";

import { useState } from "react";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { PermissionGuard } from "@/components/permission-guard";
import { approveItem, fetchOversightQueue, rejectItem } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";

function riskClass(level: "low" | "medium" | "high"): string {
  if (level === "high") return "bg-[rgba(255,109,122,0.2)] text-[var(--bad)]";
  if (level === "medium") return "bg-[rgba(241,180,89,0.2)] text-[var(--warn)]";
  return "bg-[rgba(39,209,154,0.2)] text-[var(--ok)]";
}

export default function OversightPage(): JSX.Element {
  const oversight = useLiveQuery("oversight-panel", fetchOversightQueue, { refreshInterval: 5000 });
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleAction(id: string, action: "approve" | "reject") {
    setBusyId(id);
    setMessage(null);
    try {
      const result = action === "approve" ? await approveItem(id) : await rejectItem(id);
      setMessage(result.message);
      await oversight.refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <AppShell>
      <Panel title="Human Oversight Center" subtitle="High-risk, financial, and social approvals with manual controls">
        {oversight.error ? <p className="mb-3 text-xs text-[var(--bad)]">{oversight.error}</p> : null}
        {message ? <p className="mb-3 text-xs text-[var(--ok)]">{message}</p> : null}
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Total Pending</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--text)]">{oversight.data?.totalPending ?? 0}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">High Risk</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--bad)]">{oversight.data?.highRiskActions.length ?? 0}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Financial Approvals</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--text)]">{oversight.data?.financialApprovals.length ?? 0}</p>
          </div>
        </div>
      </Panel>

      <Panel title="High-Risk Action Review" subtitle="Safety-first decision queue">
        <div className="space-y-2">
          {(oversight.data?.highRiskActions ?? []).map((item) => (
            <div key={item.id} className="rounded-xl border border-[rgba(255,109,122,0.4)] bg-[rgba(255,109,122,0.08)] p-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-[var(--text)]">{item.action}</p>
                <span className={`rounded-full px-2 py-0.5 text-xs ${riskClass(item.riskLevel)}`}>{item.riskLevel}</span>
              </div>
              <p className="mt-1 text-xs text-[var(--muted)]">Target: {item.target}</p>
              <p className="mt-1 text-xs text-[var(--muted)]">Reason: {item.reason}</p>
              <PermissionGuard permission="approve_actions" fallback={<p className="mt-2 text-xs text-[var(--warn)]">Read-only role: oversight actions disabled.</p>}>
                <div className="mt-2 flex gap-2">
                  <button className="rounded-lg bg-[var(--ok)] px-3 py-1.5 text-xs font-semibold text-[#082118] disabled:opacity-60" onClick={() => void handleAction(item.id, "approve")} disabled={busyId === item.id}>{busyId === item.id ? "Working..." : "Approve"}</button>
                  <button className="rounded-lg bg-[var(--bad)] px-3 py-1.5 text-xs font-semibold text-[#2f1014] disabled:opacity-60" onClick={() => void handleAction(item.id, "reject")} disabled={busyId === item.id}>{busyId === item.id ? "Working..." : "Reject"}</button>
                  <PermissionGuard permission="manual_override">
                    <button className="rounded-lg bg-[rgba(241,180,89,0.2)] px-3 py-1.5 text-xs font-semibold text-[var(--warn)]">Manual Override</button>
                  </PermissionGuard>
                </div>
              </PermissionGuard>
            </div>
          ))}
          {(oversight.data?.highRiskActions.length ?? 0) === 0 && !oversight.loading ? <p className="text-sm text-[var(--muted)]">No high-risk actions pending.</p> : null}
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Financial Approvals" subtitle="Invoice/payment review queue">
          <div className="space-y-2 text-xs text-[var(--muted)]">
            {(oversight.data?.financialApprovals ?? []).map((item) => (
              <div key={item.id} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
                <p className="text-sm font-semibold text-[var(--text)]">{item.action}</p>
                <p>Target: {item.target}</p>
                <p>Amount: {item.amount ?? 0}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Social Posting Approvals" subtitle="Outbound social interactions pending">
          <div className="space-y-2 text-xs text-[var(--muted)]">
            {(oversight.data?.socialApprovals ?? []).map((item) => (
              <div key={item.id} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
                <p className="text-sm font-semibold text-[var(--text)]">{item.action}</p>
                <p>Target: {item.target}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}
