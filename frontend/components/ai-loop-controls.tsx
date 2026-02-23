"use client";

import { useState } from "react";
import { Loader2, Play, RefreshCw, Square, Zap } from "lucide-react";
import { FeedbackBanner } from "@/components/feedback-banner";
import { Panel } from "@/components/panel";
import { fetchAiLoopStatus, processAllNow, processApprovedNow, startAiLoop, stopAiLoop } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { formatDateTime } from "@/lib/utils";

export function AiLoopControls(): JSX.Element {
  const loop = useLiveQuery("ai-loop-status", fetchAiLoopStatus, { refreshInterval: 5000 });
  const [busy, setBusy] = useState<"start" | "stop" | "approved" | "all" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAction(kind: "start" | "stop" | "approved" | "all"): Promise<void> {
    setBusy(kind);
    setMessage(null);
    setError(null);
    try {
      const res =
        kind === "start"
          ? await startAiLoop()
          : kind === "stop"
            ? await stopAiLoop()
            : kind === "approved"
              ? await processApprovedNow()
              : await processAllNow();
      setMessage(res.message);
      await loop.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Panel title="AI Loop Controls" subtitle="Control Claude processing loop and approval execution from UI">
      <div className="space-y-3">
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3 text-xs text-[var(--muted)]">
          <p>
            Loop status:{" "}
            <span className={loop.data?.running ? "text-[var(--ok)]" : "text-[var(--bad)]"}>
              {loop.data?.running ? "Running" : "Stopped"}
            </span>
          </p>
          <p>PID: {loop.data?.pid ?? "n/a"}</p>
          <p>Started: {loop.data?.startedAt ? formatDateTime(loop.data.startedAt) : "n/a"}</p>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void runAction("start")}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-3 py-2 text-xs font-medium text-white disabled:opacity-60"
          >
            {busy === "start" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
            Start AI Loop
          </button>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void runAction("stop")}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--bad)] px-3 py-2 text-xs font-medium text-white disabled:opacity-60"
          >
            {busy === "stop" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Square className="h-3.5 w-3.5" />}
            Stop Loop
          </button>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void runAction("approved")}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-xs font-medium text-[var(--text)] disabled:opacity-60"
          >
            {busy === "approved" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
            Process Approved
          </button>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void runAction("all")}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-xs font-medium text-[var(--text)] disabled:opacity-60"
          >
            {busy === "all" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Process All
          </button>
        </div>

        {message ? <FeedbackBanner tone="success" message={message} /> : null}
        {error ? <FeedbackBanner tone="error" message={error} /> : null}
        {loop.error ? <FeedbackBanner tone="error" message={loop.error} /> : null}
      </div>
    </Panel>
  );
}
