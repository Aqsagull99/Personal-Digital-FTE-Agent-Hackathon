"use client";

import { AlertTriangle, ShieldAlert, TriangleAlert } from "lucide-react";
import { Panel } from "@/components/panel";
import { fetchAccountingSummary, fetchExecutiveSummary, fetchOversightQueue } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";

export function CriticalAlertsRail(): JSX.Element {
  const summary = useLiveQuery("alerts-exec-summary", fetchExecutiveSummary, { refreshInterval: 9000 });
  const accounting = useLiveQuery("alerts-accounting-summary", fetchAccountingSummary, { refreshInterval: 10000 });
  const oversight = useLiveQuery("alerts-oversight", fetchOversightQueue, { refreshInterval: 7000 });

  const cards = [
    {
      label: "High-Risk Approvals",
      value: oversight.data?.highRiskActions.length ?? 0,
      tone: (oversight.data?.highRiskActions.length ?? 0) > 0 ? "warn" : "ok",
      icon: ShieldAlert
    },
    {
      label: "Stopped Watchers",
      value: summary.data?.watchersStopped ?? 0,
      tone: (summary.data?.watchersStopped ?? 0) > 0 ? "error" : "ok",
      icon: AlertTriangle
    },
    {
      label: "Cost Anomalies",
      value: accounting.data?.flaggedCosts.length ?? 0,
      tone: (accounting.data?.flaggedCosts.length ?? 0) > 0 ? "warn" : "ok",
      icon: TriangleAlert
    }
  ];

  return (
    <Panel title="Critical Alerts" subtitle="Safety-first signal board">
      <div className="space-y-2">
        {cards.map((card) => {
          const Icon = card.icon;
          const badge =
            card.tone === "error"
              ? "bg-[color-mix(in_srgb,var(--bad)_18%,transparent)] text-[var(--bad)]"
              : card.tone === "warn"
                ? "bg-[color-mix(in_srgb,var(--warn)_20%,transparent)] text-[var(--warn)]"
                : "bg-[color-mix(in_srgb,var(--ok)_18%,transparent)] text-[var(--ok)]";
          return (
            <div key={card.label} className="flex items-center justify-between rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-[var(--muted)]" />
                <p className="text-xs font-medium text-[var(--text)]">{card.label}</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badge}`}>{card.value}</span>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
