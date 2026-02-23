"use client";

import { useState } from "react";
import { Loader2, Play } from "lucide-react";
import { FeedbackBanner } from "@/components/feedback-banner";
import { Panel } from "@/components/panel";
import { processApprovedNow, runAiTask, startAiLoop, startWatcher } from "@/lib/client-api";

type Step = {
  label: string;
  status: "pending" | "running" | "success" | "error";
  detail?: string;
};

const PRESETS = {
  filesystem: {
    label: "Filesystem Inbox Flow",
    watcher: "filesystem",
    prompt:
      "Process newly detected filesystem items in Needs_Action, create plans, move sensitive actions to Pending_Approval, and execute only safe actions."
  },
  gmail: {
    label: "Gmail Inbox Flow",
    watcher: "gmail",
    prompt:
      "Process latest Gmail items in Needs_Action, create plan, flag sensitive communication for approval, and complete safe tasks."
  },
  custom: {
    label: "Custom",
    watcher: "",
    prompt: ""
  }
} as const;

export function ScenarioRunnerPanel(): JSX.Element {
  const [preset, setPreset] = useState<keyof typeof PRESETS>("filesystem");
  const [customWatcher, setCustomWatcher] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [autoProcessApproved, setAutoProcessApproved] = useState(false);
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeWatcher = preset === "custom" ? customWatcher.trim() : PRESETS[preset].watcher;
  const activePrompt = preset === "custom" ? customPrompt.trim() : PRESETS[preset].prompt;

  function initSteps(): Step[] {
    const base: Step[] = [
      { label: "Start watcher", status: "pending" },
      { label: "Queue AI task", status: "pending" },
      { label: "Start AI loop", status: "pending" }
    ];
    if (autoProcessApproved) base.push({ label: "Process approved queue", status: "pending" });
    return base;
  }

  function updateStep(index: number, patch: Partial<Step>): void {
    setSteps((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  }

  async function runScenario(): Promise<void> {
    if (!activeWatcher) {
      setError("Watcher name is required.");
      return;
    }
    if (!activePrompt) {
      setError("Prompt is required.");
      return;
    }

    setRunning(true);
    setMessage(null);
    setError(null);
    const sequence = initSteps();
    setSteps(sequence);

    try {
      updateStep(0, { status: "running" });
      const startWatcherRes = await startWatcher(activeWatcher);
      updateStep(0, { status: "success", detail: startWatcherRes.message });

      updateStep(1, { status: "running" });
      const runTaskRes = await runAiTask({
        title: `${preset.toUpperCase()} scenario`,
        prompt: activePrompt,
        priority: "high",
        source: "scenario_runner"
      });
      updateStep(1, { status: "success", detail: runTaskRes.message });

      updateStep(2, { status: "running" });
      const loopRes = await startAiLoop();
      updateStep(2, { status: "success", detail: loopRes.message });

      if (autoProcessApproved) {
        const idx = 3;
        updateStep(idx, { status: "running" });
        const approvedRes = await processApprovedNow();
        updateStep(idx, { status: "success", detail: approvedRes.message });
      }

      setMessage("Scenario executed. Monitor Needs Action, Pending Approval, and Done for progress.");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Scenario failed";
      const runningIdx = steps.findIndex((s) => s.status === "running");
      if (runningIdx >= 0) updateStep(runningIdx, { status: "error", detail: msg });
      setError(msg);
    } finally {
      setRunning(false);
    }
  }

  return (
    <Panel title="Scenario Runner" subtitle="One-click execution: start watcher, queue task, and start loop">
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="space-y-1">
            <span className="text-xs text-[var(--muted)]">Scenario preset</span>
            <select
              value={preset}
              onChange={(event) => setPreset(event.target.value as keyof typeof PRESETS)}
              className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)]"
            >
              <option value="filesystem">{PRESETS.filesystem.label}</option>
              <option value="gmail">{PRESETS.gmail.label}</option>
              <option value="custom">{PRESETS.custom.label}</option>
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs text-[var(--muted)]">Watcher</span>
            <input
              type="text"
              value={preset === "custom" ? customWatcher : PRESETS[preset].watcher}
              onChange={(event) => setCustomWatcher(event.target.value)}
              disabled={preset !== "custom"}
              className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] disabled:opacity-60"
            />
          </label>
        </div>

        <label className="space-y-1">
          <span className="text-xs text-[var(--muted)]">Prompt</span>
          <textarea
            rows={3}
            value={preset === "custom" ? customPrompt : PRESETS[preset].prompt}
            onChange={(event) => setCustomPrompt(event.target.value)}
            disabled={preset !== "custom"}
            className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] disabled:opacity-60"
          />
        </label>

        <label className="inline-flex items-center gap-2 text-xs text-[var(--muted)]">
          <input
            type="checkbox"
            checked={autoProcessApproved}
            onChange={(event) => setAutoProcessApproved(event.target.checked)}
            className="rounded border-[var(--line)]"
          />
          Also run `Process Approved` at the end
        </label>

        <button
          type="button"
          onClick={() => void runScenario()}
          disabled={running}
          className="inline-flex items-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {running ? "Running Scenario..." : "Run Scenario"}
        </button>

        {steps.length > 0 ? (
          <div className="space-y-2 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-3">
            {steps.map((step) => (
              <div key={step.label} className="text-xs">
                <p className="text-[var(--text)]">
                  {step.status === "running" ? "⏳" : step.status === "success" ? "✓" : step.status === "error" ? "✕" : "•"} {step.label}
                </p>
                {step.detail ? <p className="ml-4 text-[var(--muted)]">{step.detail}</p> : null}
              </div>
            ))}
          </div>
        ) : null}

        {message ? <FeedbackBanner tone="success" message={message} /> : null}
        {error ? <FeedbackBanner tone="error" message={error} /> : null}
      </div>
    </Panel>
  );
}
