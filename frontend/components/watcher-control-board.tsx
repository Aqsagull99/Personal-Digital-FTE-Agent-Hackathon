"use client";

import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { fetchWatchers, startWatcher, stopWatcher } from "@/lib/client-api";
import type { WatcherControlItem } from "@/lib/types";
import { useLiveQuery } from "@/lib/use-live-query";
import { type AccessTier, TIER_WATCHERS, hasTierAccess, normalizeWatcherName, watcherLabel } from "@/lib/watcher-tiers";
import { useTier } from "@/lib/use-tier";
import { formatDateTime } from "@/lib/utils";

function statusTone(status: "running" | "stopped" | "transition"): string {
  if (status === "running") return "bg-[rgba(17,154,111,0.18)] text-[var(--ok)]";
  if (status === "transition") return "bg-[rgba(183,121,31,0.22)] text-[var(--warn)]";
  return "bg-[rgba(214,69,93,0.16)] text-[var(--bad)]";
}

type Props = {
  requiredTier: AccessTier;
};

export function WatcherControlBoard({ requiredTier }: Props): JSX.Element {
  const { tier } = useTier();
  const canUseTier = hasTierAccess(tier, requiredTier);
  const effectiveTier: AccessTier = canUseTier ? requiredTier : tier;
  const live = useLiveQuery("watchers", fetchWatchers, { refreshInterval: 10000 });
  const [busy, setBusy] = useState<Record<string, "starting" | "stopping" | undefined>>({});
  const [notice, setNotice] = useState<string | null>(null);

  const visibleWatchers = useMemo(() => {
    const allowed = new Set(TIER_WATCHERS[effectiveTier]);
    return (live.data ?? []).filter((watcher) => allowed.has(normalizeWatcherName(watcher.name)));
  }, [effectiveTier, live.data]);

  async function onToggle(watcher: WatcherControlItem): Promise<void> {
    const key = normalizeWatcherName(watcher.name);
    const action = watcher.running ? "stopping" : "starting";
    setBusy((prev) => ({ ...prev, [key]: action }));
    setNotice(null);
    try {
      const response = watcher.running ? await stopWatcher(key) : await startWatcher(key);
      setNotice(response.message);
      await live.refresh();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Failed to update watcher");
    } finally {
      setBusy((prev) => ({ ...prev, [key]: undefined }));
    }
  }

  return (
    <div className="space-y-3">
      {notice ? (
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--muted)]">
          {notice}
        </div>
      ) : null}
      {!canUseTier ? (
        <div className="rounded-xl border border-[rgba(183,121,31,0.45)] bg-[rgba(183,121,31,0.1)] px-3 py-2 text-xs text-[var(--warn)]">
          Current tier is {tier}. Upgrade to {requiredTier} to unlock additional watchers.
        </div>
      ) : null}
      {live.error ? (
        <div className="rounded-xl border border-[rgba(214,69,93,0.45)] bg-[rgba(214,69,93,0.1)] px-3 py-2 text-sm text-[var(--bad)]">
          {live.error}
        </div>
      ) : null}
      <div className="grid gap-4 md:grid-cols-2">
        {visibleWatchers.map((watcher) => {
          const key = normalizeWatcherName(watcher.name);
          const transition = busy[key];
          const status = transition ? "transition" : watcher.running ? "running" : "stopped";
          const disableControl = transition !== undefined;
          return (
            <article key={key} className={`rounded-2xl border border-[var(--line)] bg-[var(--surface-2)] p-4 shadow-sm ${!canUseTier ? "opacity-70" : ""}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--text)]">{watcherLabel(watcher.name)}</h3>
                  <p className="mt-1 text-xs text-[var(--muted)]">{watcher.script}</p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusTone(status)}`}>
                  {status === "transition" ? (transition === "starting" ? "Starting" : "Stopping") : watcher.running ? "Running" : "Stopped"}
                </span>
              </div>
              <div className="mt-3 space-y-1 text-xs text-[var(--muted)]">
                <p>Last activity: {watcher.lastActivity ? formatDateTime(watcher.lastActivity) : "No activity yet"}</p>
                <p>PID: {watcher.pid ?? "n/a"}</p>
              </div>
              <div className="mt-4 flex items-center justify-between gap-3">
                <span />
                <button
                  type="button"
                  disabled={disableControl}
                  onClick={() => void onToggle(watcher)}
                  className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-white ${
                    watcher.running ? "bg-[var(--bad)] hover:opacity-90" : "bg-[var(--accent)] hover:opacity-90"
                  } disabled:cursor-not-allowed disabled:opacity-50`}
                >
                  {transition ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  {watcher.running ? "Stop" : "Start"}
                </button>
              </div>
            </article>
          );
        })}
      </div>
      {live.loading && visibleWatchers.length === 0 ? <p className="text-sm text-[var(--muted)]">Loading watchers...</p> : null}
      {!live.loading && visibleWatchers.length === 0 ? <p className="text-sm text-[var(--muted)]">No watchers available for this tier.</p> : null}
    </div>
  );
}
