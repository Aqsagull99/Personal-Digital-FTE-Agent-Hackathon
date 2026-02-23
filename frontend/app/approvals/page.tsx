"use client";

import { useMemo, useState } from "react";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { PermissionGuard } from "@/components/permission-guard";
import { approveItem, fetchApprovalDetail, fetchApprovals, rejectItem } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";

function riskClass(level: "low" | "medium" | "high"): string {
  if (level === "high") return "bg-[rgba(214,69,93,0.18)] text-[var(--bad)] border-[rgba(214,69,93,0.35)]";
  if (level === "medium") return "bg-[rgba(183,121,31,0.18)] text-[var(--warn)] border-[rgba(183,121,31,0.35)]";
  return "bg-[rgba(17,154,111,0.18)] text-[var(--ok)] border-[rgba(17,154,111,0.35)]";
}

export default function ApprovalCenterPage(): JSX.Element {
  const approvalsQuery = useLiveQuery("approvals", fetchApprovals, { refreshInterval: 6000 });
  const approvals = useMemo(() => approvalsQuery.data ?? [], [approvalsQuery.data]);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const detail = useLiveQuery(
    selectedId ? `approval-detail-${selectedId}` : null,
    selectedId ? () => fetchApprovalDetail(selectedId) : null,
    { refreshInterval: 6000 }
  );

  const selected = useMemo(() => approvals.find((item) => item.id === selectedId) ?? detail.data ?? null, [approvals, selectedId, detail.data]);

  async function handleAction(action: "approve" | "reject") {
    if (!selected) return;
    setBusy(selected.id);
    setMessage(null);
    try {
      const result = action === "approve" ? await approveItem(selected.id) : await rejectItem(selected.id);
      setMessage(result.message);
      setSelectedId(null);
      await approvalsQuery.refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `Failed to ${action}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <AppShell>
      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel
          title="Pending Approvals"
          subtitle="Risk-ranked requests requiring human confirmation"
          action={<button className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm text-white" onClick={() => void approvalsQuery.refresh()}>{approvalsQuery.loading ? "Loading..." : "Refresh"}</button>}
        >
          {approvalsQuery.error ? <p className="mb-3 text-xs text-[var(--bad)]">{approvalsQuery.error}</p> : null}
          <div className="space-y-2">
            {approvals.map((item) => (
              <button
                key={item.id}
                className={`w-full rounded-xl border p-3 text-left transition ${selectedId === item.id ? "border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)]" : item.riskLevel === "high" ? "border-[rgba(214,69,93,0.4)] bg-[rgba(214,69,93,0.08)]" : "border-[var(--line)] bg-[var(--surface-2)] hover:border-[var(--accent)]"}`}
                onClick={() => setSelectedId(item.id)}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-[var(--text)]">{item.action}</p>
                  <span className={`rounded-full border px-2 py-0.5 text-xs ${riskClass(item.riskLevel)}`}>{item.riskLevel}</span>
                </div>
                <p className="mt-1 text-xs text-[var(--muted)]">{item.target}</p>
                <p className="mt-1 text-xs text-[var(--muted)]">Requested: {new Date(item.requestedAt).toLocaleString()}</p>
              </button>
            ))}
            {approvals.length === 0 && !approvalsQuery.loading ? <p className="text-sm text-[var(--muted)]">No pending approvals.</p> : null}
          </div>
        </Panel>

        <Panel title="Approval Detail" subtitle="Color-coded decision controls">
          {message ? <p className="mb-3 text-xs text-[var(--ok)]">{message}</p> : null}
          {detail.error ? <p className="mb-3 text-xs text-[var(--bad)]">{detail.error}</p> : null}
          {selected ? (
            <div className="space-y-3 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-[var(--text)]">{selected.action}</h3>
                <span className={`rounded-full border px-2 py-0.5 text-xs ${riskClass(selected.riskLevel)}`}>{selected.riskLevel} risk</span>
              </div>
              <p className="text-sm text-[var(--muted)]">Target: {selected.target}</p>
              <p className="text-sm text-[var(--muted)]">Reason: {selected.reason}</p>
              {selected.amount ? <p className="text-sm text-[var(--muted)]">Amount: ${selected.amount}</p> : null}
              <PermissionGuard permission="approve_actions" fallback={<p className="text-xs text-[var(--warn)]">Read-only role: approval actions disabled.</p>}>
                <div className="flex gap-2">
                  <button className="rounded-lg bg-[var(--ok)] px-3 py-2 text-sm font-semibold text-[#06251a] disabled:opacity-60" disabled={busy === selected.id} onClick={() => void handleAction("approve")}>{busy === selected.id ? "Working..." : "Approve"}</button>
                  <button className="rounded-lg bg-[var(--bad)] px-3 py-2 text-sm font-semibold text-[#fff] disabled:opacity-60" disabled={busy === selected.id} onClick={() => void handleAction("reject")}>{busy === selected.id ? "Working..." : "Reject"}</button>
                </div>
              </PermissionGuard>
            </div>
          ) : (
            <p className="text-sm text-[var(--muted)]">Select an approval request to inspect details.</p>
          )}
        </Panel>
      </div>
    </AppShell>
  );
}
