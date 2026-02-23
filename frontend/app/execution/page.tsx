"use client";

import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchExecutionMonitor } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";

export default function ExecutionPage(): JSX.Element {
  const execution = useLiveQuery("execution-panel", fetchExecutionMonitor, { refreshInterval: 5000 });
  const data = execution.data;

  return (
    <AppShell>
      <Panel title="Autonomous Execution Monitor" subtitle="Running tasks, multi-step plans, loop tracking">
        {execution.error ? <p className="mb-3 text-xs text-[var(--bad)]">{execution.error}</p> : null}
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Current Running Tasks</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--text)]">{data?.runningTasks.length ?? 0}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Loop Iterations</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--text)]">{data?.loopIterationCount ?? 0}</p>
          </div>
          <div className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
            <p className="text-xs text-[var(--muted)]">Completion Promises</p>
            <p className="mt-1 text-2xl font-semibold text-[var(--text)]">{data?.completionPromisesDetected ?? 0}</p>
          </div>
        </div>
      </Panel>

      <Panel title="Running Task Queue" subtitle="Execution state with progress tracking">
        <div className="space-y-2">
          {(data?.runningTasks ?? []).map((task) => (
            <div key={task.id} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-[var(--text)]">{task.title}</p>
                <span className="text-xs text-[var(--muted)]">{task.status}</span>
              </div>
              <p className="mt-1 text-xs text-[var(--muted)]">Source: {task.source}</p>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-[rgba(255,255,255,0.08)]">
                <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${task.progress}%` }} />
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Plan Visualization" subtitle="Multi-step reasoning plans">
        <div className="space-y-3">
          {(data?.planVisualization ?? []).map((plan) => (
            <article key={plan.id} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[var(--text)]">{plan.title}</h3>
                <span className="text-xs text-[var(--muted)]">{plan.progress}%</span>
              </div>
              <ul className="mt-2 space-y-1 text-xs text-[var(--muted)]">
                {plan.steps.map((step) => (
                  <li key={step.label}>[{step.done ? "x" : " "}] {step.label}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </Panel>
    </AppShell>
  );
}
