"use client";

import { useMemo, useState } from "react";
import { AlertOctagon, BadgeAlert, Bot, CircleDollarSign, Timer, TriangleAlert } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "@/components/shell";
import { AiLoopControls } from "@/components/ai-loop-controls";
import { CriticalAlertsRail } from "@/components/critical-alerts-rail";
import { CreateDraftPanel } from "@/components/create-draft-panel";
import { Panel } from "@/components/panel";
import { RunAiTaskPanel } from "@/components/run-ai-task-panel";
import { ScenarioRunnerPanel } from "@/components/scenario-runner-panel";
import { StatCard } from "@/components/stat-card";
import { fetchAccountingSummary, fetchExecutiveSummary, fetchExecutionMonitor, fetchLogs, fetchOversightQueue } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { useOpsStore } from "@/lib/ops-store";
import { formatDateTime } from "@/lib/utils";

type TrendWindow = "24h" | "7d" | "30d";

export default function AutonomousDashboardPage(): JSX.Element {
  const [trendWindow, setTrendWindow] = useState<TrendWindow>("7d");

  const summary = useLiveQuery("exec-summary", fetchExecutiveSummary, { refreshInterval: 8000 });
  const accounting = useLiveQuery("accounting-summary", fetchAccountingSummary, { refreshInterval: 10000 });
  const execution = useLiveQuery("execution-monitor", fetchExecutionMonitor, { refreshInterval: 7000 });
  const oversight = useLiveQuery("oversight-queue", fetchOversightQueue, { refreshInterval: 6000 });
  const logs = useLiveQuery("dashboard-logs", () => fetchLogs({ limit: 250 }), { refreshInterval: 12000 });

  const wsConnected = useOpsStore((s) => s.wsConnected);
  const wsSummary = useOpsStore((s) => s.liveSummary);
  const lastEventAt = useOpsStore((s) => s.lastEventAt);

  const revenueSeries = useMemo(
    () => wsSummary?.revenueSeries ?? accounting.data?.monthlyRevenue ?? summary.data?.revenueSeries ?? [],
    [wsSummary?.revenueSeries, accounting.data?.monthlyRevenue, summary.data?.revenueSeries]
  );
  const pendingHighRisk = oversight.data?.highRiskActions.length ?? 0;
  const loops = execution.data?.loopIterationCount ?? 0;
  const completionPromises = execution.data?.completionPromisesDetected ?? 0;
  const bottleneck = (summary.data?.activeTaskCount ?? 0) > 20 || pendingHighRisk > 5;
  const costAnomalies = accounting.data?.flaggedCosts.length ?? 0;
  const trendWindowStart = useMemo(() => {
    const now = Date.now();
    if (trendWindow === "24h") return now - (24 * 60 * 60 * 1000);
    if (trendWindow === "7d") return now - (7 * 24 * 60 * 60 * 1000);
    return now - (30 * 24 * 60 * 60 * 1000);
  }, [trendWindow]);

  const filteredLogs = useMemo(() => {
    return (logs.data ?? []).filter((entry) => {
      const ts = Date.parse(entry.timestamp);
      return Number.isFinite(ts) && ts >= trendWindowStart;
    });
  }, [logs.data, trendWindowStart]);

  const trendLabel = trendWindow === "24h" ? "24 hours" : trendWindow === "7d" ? "7 days" : "30 days";

  const trendRevenueSeries = useMemo(() => {
    const points = revenueSeries ?? [];
    const take = trendWindow === "24h" ? 6 : trendWindow === "7d" ? 12 : 24;
    return points.slice(-Math.max(2, take));
  }, [revenueSeries, trendWindow]);

  const topBottlenecks = useMemo(() => {
    const reasons: string[] = [];
    if ((summary.data?.activeTaskCount ?? 0) > 20) reasons.push("High active task backlog");
    if (pendingHighRisk > 5) reasons.push("High-risk approvals building up");
    if ((summary.data?.watchersStopped ?? 0) > 0) reasons.push("Some watchers are stopped");
    if (costAnomalies > 0) reasons.push("Cost anomalies detected");
    return reasons;
  }, [summary.data?.activeTaskCount, summary.data?.watchersStopped, pendingHighRisk, costAnomalies]);

  const channelSeries = useMemo(() => {
    const counts: Record<string, number> = {
      email: 0,
      payment: 0,
      social: 0,
      system: 0,
      file: 0,
      other: 0
    };
    for (const entry of filteredLogs) {
      counts[entry.channel] = (counts[entry.channel] ?? 0) + 1;
    }
    return Object.entries(counts).map(([channel, value]) => ({
      channel: channel.toUpperCase(),
      value
    }));
  }, [filteredLogs]);

  const opsRiskSeries = useMemo(() => {
    const buckets = new Map<number, { label: string; load: number; risk: number; anomaly: number }>();

    const getBucket = (timestamp: number): { key: number; label: string } => {
      const date = new Date(timestamp);
      if (trendWindow === "24h") {
        const key = new Date(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours()).getTime();
        const label = `${String(date.getHours()).padStart(2, "0")}:00`;
        return { key, label };
      }
      const key = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
      const label = `${date.getMonth() + 1}/${date.getDate()}`;
      return { key, label };
    };

    for (const entry of filteredLogs) {
      const ts = Date.parse(entry.timestamp);
      if (!Number.isFinite(ts)) continue;
      const bucket = getBucket(ts);
      const current = buckets.get(bucket.key) ?? { label: bucket.label, load: 0, risk: 0, anomaly: 0 };
      current.load += 1;

      const isRisk = entry.status === "failed" || entry.channel === "payment" || entry.actionType.toLowerCase().includes("approval");
      if (isRisk) current.risk += 1;

      const isAnomaly = (entry.channel === "payment" && entry.status === "failed") || entry.actionType.toLowerCase().includes("anomaly");
      if (isAnomaly) current.anomaly += 1;

      buckets.set(bucket.key, current);
    }

    return Array.from(buckets.entries())
      .sort(([a], [b]) => a - b)
      .map(([, value]) => value);
  }, [filteredLogs, trendWindow]);

  const revenueSpark = trendRevenueSeries.map((point) => point.value);
  const loadSpark = opsRiskSeries.map((point) => point.load);
  const riskSpark = opsRiskSeries.map((point) => point.risk);
  const anomalySpark = opsRiskSeries.map((point) => point.anomaly);

  const watcherHealthMix = useMemo(() => {
    const counts = { healthy: 0, degraded: 0, offline: 0 };
    for (const item of summary.data?.watcherHealth ?? []) {
      counts[item.status] += 1;
    }
    return [
      { name: "Healthy", value: counts.healthy, color: "var(--ok)" },
      { name: "Degraded", value: counts.degraded, color: "var(--warn)" },
      { name: "Offline", value: counts.offline, color: "var(--bad)" }
    ];
  }, [summary.data?.watcherHealth]);

  return (
    <AppShell>
      <div className="flex items-center justify-between rounded-2xl border border-[var(--line)] bg-[var(--surface-1)] px-4 py-2 text-xs text-[var(--muted)] shadow-sm">
        <span>Autonomous AI Operations Console {wsConnected ? "(WebSocket live)" : "(SWR polling mode)"}</span>
        <span>{lastEventAt ? `Last live event: ${formatDateTime(lastEventAt)}` : "No live event yet"}</span>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Revenue vs Target" value={`$${(summary.data?.revenueTotal ?? 0).toLocaleString()}`} note={`Target tracking active • ERP ${accounting.data?.erpSyncStatus ?? "n/a"}`} icon={CircleDollarSign} sparkline={revenueSpark} />
        <StatCard label="Active Loops" value={String(loops)} note={`Completion promises: ${completionPromises}`} icon={Bot} sparkline={loadSpark} />
        <StatCard label="High-Risk Pending" value={String(pendingHighRisk)} note="Safety-critical actions awaiting review" icon={BadgeAlert} sparkline={riskSpark} />
        <StatCard label="Cost Anomalies" value={String(costAnomalies)} note={costAnomalies > 0 ? "Requires financial oversight" : "No anomalies currently"} icon={TriangleAlert} sparkline={anomalySpark} />
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Operations Hub</h2>
          <span className="text-xs text-[var(--muted)]">Run tasks, drafts, and loop controls</span>
        </div>
        <div className="grid gap-4 xl:grid-cols-4">
          <div className="xl:col-span-3">
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <RunAiTaskPanel />
              </div>
              <AiLoopControls />
              <div className="lg:col-span-3">
                <ScenarioRunnerPanel />
              </div>
              <div className="lg:col-span-3">
                <CreateDraftPanel />
              </div>
            </div>
          </div>
          <div className="xl:col-span-1">
            <CriticalAlertsRail />
          </div>
        </div>
      </section>

      <section className="flex items-center justify-between rounded-2xl border border-[var(--line)] bg-[var(--surface-1)] px-4 py-2">
        <div>
          <p className="text-sm font-semibold text-[var(--text)]">Trend Window</p>
          <p className="text-xs text-[var(--muted)]">Analytics scope: last {trendLabel}</p>
        </div>
        <div className="inline-flex rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-1">
          {(["24h", "7d", "30d"] as TrendWindow[]).map((windowKey) => (
            <button
              key={windowKey}
              type="button"
              onClick={() => setTrendWindow(windowKey)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                trendWindow === windowKey
                  ? "bg-[color-mix(in_srgb,var(--accent)_20%,transparent)] text-[var(--text)]"
                  : "text-[var(--muted)] hover:text-[var(--text)]"
              }`}
            >
              {windowKey}
            </button>
          ))}
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Revenue vs Target Trend" subtitle="Monthly revenue trajectory from accounting logs">
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendRevenueSeries}>
                <defs>
                  <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f7cff" stopOpacity={0.55} />
                    <stop offset="95%" stopColor="#4f7cff" stopOpacity={0.08} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
                <XAxis dataKey="date" stroke="var(--muted)" />
                <YAxis stroke="var(--muted)" />
                <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: "12px", color: "var(--text)" }} formatter={(v: number) => [`$${Number(v).toLocaleString()}`, "Revenue"]} />
                <Area type="monotone" dataKey="value" stroke="#4f7cff" fill="url(#rev)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Operational Risk Signals" subtitle="Bottlenecks, anomalies, and safety pressure">
          <div className="space-y-2">
            <div className="h-44 w-full rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={opsRiskSeries}>
                  <defs>
                    <linearGradient id="opsLoad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="var(--accent)" stopOpacity={0.08} />
                    </linearGradient>
                    <linearGradient id="opsRisk" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--bad)" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="var(--bad)" stopOpacity={0.08} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
                  <XAxis dataKey="label" stroke="var(--muted)" tick={{ fontSize: 11 }} />
                  <YAxis stroke="var(--muted)" tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: "12px", color: "var(--text)" }} />
                  <Area type="monotone" dataKey="load" name="Ops Load" stackId="ops" stroke="var(--accent)" fill="url(#opsLoad)" />
                  <Area type="monotone" dataKey="risk" name="Risk Pressure" stackId="ops" stroke="var(--bad)" fill="url(#opsRisk)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className={`rounded-xl border p-3 ${bottleneck ? "border-[rgba(214,69,93,0.42)] bg-[rgba(214,69,93,0.1)]" : "border-[rgba(17,154,111,0.42)] bg-[rgba(17,154,111,0.08)]"}`}>
              <p className="text-sm font-semibold text-[var(--text)]">Bottleneck Detection</p>
              <p className="text-xs text-[var(--muted)]">{bottleneck ? "Bottleneck detected in current operations." : "No major bottlenecks detected."}</p>
              <span className={`mt-2 inline-flex rounded-full px-2 py-0.5 text-xs ${bottleneck ? "bg-[rgba(214,69,93,0.16)] text-[var(--bad)]" : "bg-[rgba(17,154,111,0.16)] text-[var(--ok)]"}`}>{bottleneck ? "Failed" : "Running"}</span>
            </div>
            <div className={`rounded-xl border p-3 ${costAnomalies > 0 ? "border-[rgba(183,121,31,0.45)] bg-[rgba(183,121,31,0.1)]" : "border-[var(--line)] bg-[var(--surface-2)]"}`}>
              <p className="text-sm font-semibold text-[var(--text)]">Cost Anomaly Alerts</p>
              <p className="text-xs text-[var(--muted)]">{costAnomalies} flagged cost events.</p>
              <span className={`mt-2 inline-flex rounded-full px-2 py-0.5 text-xs ${costAnomalies > 0 ? "bg-[rgba(183,121,31,0.2)] text-[var(--warn)]" : "bg-[color-mix(in_srgb,var(--accent)_14%,transparent)] text-[var(--accent)]"}`}>{costAnomalies > 0 ? "Pending" : "Running"}</span>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3">
              <p className="text-sm font-semibold text-[var(--text)]">Top Bottleneck Drivers</p>
              <ul className="mt-2 list-disc pl-5 text-xs text-[var(--muted)]">
                {(topBottlenecks.length > 0 ? topBottlenecks : ["No active bottleneck drivers"]).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Channel Activity Mix" subtitle={`Log volume by action channel (last ${trendLabel})`}>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={channelSeries}>
                <CartesianGrid stroke="var(--line)" strokeDasharray="4 4" />
                <XAxis dataKey="channel" stroke="var(--muted)" />
                <YAxis stroke="var(--muted)" />
                <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: "12px", color: "var(--text)" }} />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {channelSeries.map((entry) => (
                    <Cell
                      key={entry.channel}
                      fill={
                        entry.channel === "EMAIL"
                          ? "var(--accent)"
                          : entry.channel === "PAYMENT"
                            ? "var(--warn)"
                            : entry.channel === "SOCIAL"
                              ? "var(--ok)"
                              : "color-mix(in_srgb,var(--accent)_35%,var(--surface-2))"
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Watcher Health Ring" subtitle="Current operational health distribution">
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={watcherHealthMix} dataKey="value" nameKey="name" innerRadius={70} outerRadius={110} paddingAngle={3}>
                  {watcherHealthMix.map((slice) => (
                    <Cell key={slice.name} fill={slice.color} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: "12px", color: "var(--text)" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <Panel title="Live Activity Feed" subtitle="Recent autonomous events and high-risk pressure">
        <div className="space-y-2">
          {(summary.data?.recentActivity ?? []).slice(0, 12).map((event) => (
            <div key={event.id} className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-[var(--text)]">{event.actionType}</p>
                <span className={`rounded-full px-2 py-0.5 text-xs ${event.status === "success" ? "bg-[rgba(17,154,111,0.18)] text-[var(--ok)]" : "bg-[rgba(214,69,93,0.16)] text-[var(--bad)]"}`}>{event.status}</span>
              </div>
              <p className="mt-1 text-xs text-[var(--muted)]">{event.actor} → {event.target}</p>
              <p className="mt-1 text-xs text-[var(--muted)]">{formatDateTime(event.timestamp)}</p>
            </div>
          ))}
        </div>
      </Panel>

      {(summary.loading || accounting.loading || execution.loading || oversight.loading) ? (
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-1)] p-3 text-xs text-[var(--muted)] shadow-sm">
          <Timer className="mr-2 inline h-4 w-4" />
          Synchronizing autonomous telemetry...
        </div>
      ) : null}

      {(summary.error || accounting.error || execution.error || oversight.error) ? (
        <div className="rounded-xl border border-[rgba(214,69,93,0.45)] bg-[rgba(214,69,93,0.1)] p-3 text-xs text-[var(--bad)]">
          <AlertOctagon className="mr-2 inline h-4 w-4" />
          {summary.error || accounting.error || execution.error || oversight.error}
        </div>
      ) : null}
    </AppShell>
  );
}
