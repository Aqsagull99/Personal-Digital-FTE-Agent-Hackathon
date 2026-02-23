"use client";

import Link from "next/link";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchTasks } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { formatDateTime, priorityTone } from "@/lib/utils";

export default function InboxPage(): JSX.Element {
  const tasksQuery = useLiveQuery("needs-action", fetchTasks, { refreshInterval: 7000 });
  const tasks = tasksQuery.data ?? [];

  return (
    <AppShell>
      <Panel
        title="Needs Action"
        subtitle="Live task queue from /Needs_Action"
        action={<button className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm text-white" onClick={() => void tasksQuery.refresh()}>{tasksQuery.loading ? "Loading..." : "Refresh"}</button>}
      >
        {tasksQuery.error ? <p className="mb-3 text-xs text-[var(--bad)]">{tasksQuery.error}</p> : null}
        <div className="grid gap-4 md:grid-cols-2">
          {tasks.map((task) => (
            <Link key={task.id} href={`/inbox/${encodeURIComponent(task.id)}`} className="rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-4 transition hover:border-[var(--accent)]">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-[0.12em] text-[var(--muted)]">{task.type}</p>
                <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${priorityTone(task.priority)}`}>{task.priority}</span>
              </div>
              <h3 className="mt-2 font-semibold text-[var(--text)]">{task.title}</h3>
              <p className="mt-2 text-sm text-[var(--muted)]">{task.preview}</p>
              <div className="mt-3 flex items-center justify-between text-xs text-[var(--muted)]">
                <span>{task.source}</span>
                <span>{formatDateTime(task.received)}</span>
              </div>
            </Link>
          ))}
          {tasks.length === 0 && !tasksQuery.loading ? <p className="text-sm text-[var(--muted)]">No items in needs-action queue.</p> : null}
        </div>
      </Panel>
    </AppShell>
  );
}
