"use client";

import { useState } from "react";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { StatCard } from "@/components/stat-card";
import { TierSelector } from "@/components/tier-selector";
import { WatcherControlBoard } from "@/components/watcher-control-board";
import { CheckCircle2, Clock3, ShieldAlert, Workflow } from "lucide-react";
import { cleanupNeedsAction, fetchApprovals, fetchExecutiveSummary, fetchTasks, fetchWatchers } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";

export default function DashboardPage(): JSX.Element {
  const tasks = useLiveQuery("tasks", fetchTasks, { refreshInterval: 10000 });
  const approvals = useLiveQuery("approvals", fetchApprovals, { refreshInterval: 10000 });
  const summary = useLiveQuery("exec-summary", fetchExecutiveSummary, { refreshInterval: 10000 });
  const watchers = useLiveQuery("watchers", fetchWatchers, { refreshInterval: 10000 });

  const pendingTaskCount = (tasks.data ?? []).filter((task) => task.status === "pending" || task.status === "in_progress").length;
  const pendingApprovals = approvals.data?.length ?? 0;
  const completedTasks = summary.data?.completedTaskCount ?? 0;
  const watchersRunning = (watchers.data ?? []).filter((item) => item.running).length;
  const watchersStopped = (watchers.data ?? []).length - watchersRunning;
  const [cleanupMsg, setCleanupMsg] = useState<string | null>(null);
  const [cleanupLoading, setCleanupLoading] = useState<"dry" | "delete" | null>(null);

  async function runCleanup(dryRun: boolean): Promise<void> {
    setCleanupLoading(dryRun ? "dry" : "delete");
    try {
      const res = await cleanupNeedsAction("ACTION_DAILY_BRIEFING_2026-02-11_*.md", dryRun);
      setCleanupMsg(res.message);
      await tasks.refresh();
    } catch (err) {
      setCleanupMsg(err instanceof Error ? err.message : "Cleanup failed");
    } finally {
      setCleanupLoading(null);
    }
  }

  return (
    <AppShell>
      <Panel
        title="Dashboard"
        subtitle="Autonomous watcher operations and approval flow"
        action={<TierSelector />}
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Pending Tasks" value={String(pendingTaskCount)} note="Needs action + in-progress queue" icon={Clock3} />
          <StatCard label="Approvals Pending" value={String(pendingApprovals)} note="Human-in-the-loop approvals" icon={ShieldAlert} />
          <StatCard label="Completed Tasks" value={String(completedTasks)} note="Successfully completed actions" icon={CheckCircle2} />
          <StatCard
            label="System Status"
            value={watchersStopped > 0 ? "Degraded" : "Running"}
            note={`${watchersRunning} running / ${watchersStopped} stopped`}
            icon={Workflow}
          />
        </div>
      </Panel>

      <Panel title="Watcher Control" subtitle="Fast controls with 10s status refresh">
        <WatcherControlBoard requiredTier="gold" />
      </Panel>

      <Panel title="Cleanup Tools" subtitle="One-click duplicate cleanup for known test flood patterns">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={cleanupLoading !== null}
            onClick={() => void runCleanup(true)}
            className="rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--text)] disabled:opacity-60"
          >
            {cleanupLoading === "dry" ? "Checking..." : "Dry Run Daily-Briefing Duplicates"}
          </button>
          <button
            type="button"
            disabled={cleanupLoading !== null}
            onClick={() => void runCleanup(false)}
            className="rounded-lg bg-[var(--bad)] px-3 py-2 text-xs text-white disabled:opacity-60"
          >
            {cleanupLoading === "delete" ? "Deleting..." : "Delete Daily-Briefing Duplicates"}
          </button>
        </div>
        {cleanupMsg ? <p className="mt-2 text-xs text-[var(--muted)]">{cleanupMsg}</p> : null}
      </Panel>
    </AppShell>
  );
}
