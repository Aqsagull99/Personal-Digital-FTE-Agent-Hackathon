"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchTaskDetail } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { formatDateTime, priorityTone } from "@/lib/utils";

export default function TaskDetailPage(): JSX.Element {
  const params = useParams<{ id: string }>();
  const taskId = Array.isArray(params.id) ? params.id[0] : params.id;

  const detailQuery = useLiveQuery(taskId ? `task-${taskId}` : null, taskId ? () => fetchTaskDetail(taskId) : null, { refreshInterval: 9000 });
  const task = detailQuery.data;

  return (
    <AppShell>
      <Panel
        title="Task Detail"
        subtitle="Detailed vault record"
        action={
          <div className="flex gap-2">
            <button className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm text-white" onClick={() => void detailQuery.refresh()}>{detailQuery.loading ? "Loading..." : "Refresh"}</button>
            <Link href="/inbox" className="rounded-lg bg-[rgba(79,124,255,0.2)] px-3 py-1.5 text-sm text-white">Back</Link>
          </div>
        }
      >
        {detailQuery.error ? <p className="mb-3 text-xs text-[var(--bad)]">{detailQuery.error}</p> : null}
        {task ? (
          <article className="space-y-4 rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold text-[var(--text)]">{task.title}</h3>
              <span className={`rounded-full border px-2.5 py-1 text-xs ${priorityTone(task.priority)}`}>{task.priority}</span>
            </div>
            <p className="text-sm text-[var(--muted)]">{task.preview}</p>
            <div className="grid gap-2 text-xs text-[var(--muted)] md:grid-cols-2">
              <p>Type: {task.type}</p>
              <p>Status: {task.status}</p>
              <p>Source: {task.source}</p>
              <p>Received: {formatDateTime(task.received)}</p>
              <p className="md:col-span-2">File: {task.filePath}</p>
            </div>
            <section>
              <h4 className="mb-2 text-sm font-semibold text-[var(--text)]">Metadata</h4>
              <pre className="overflow-auto rounded-lg bg-[rgba(7,11,18,0.95)] p-3 text-xs text-[var(--text)]">{JSON.stringify(task.metadata, null, 2)}</pre>
            </section>
            <section>
              <h4 className="mb-2 text-sm font-semibold text-[var(--text)]">Markdown Content</h4>
              <pre className="max-h-[50vh] overflow-auto rounded-lg bg-[rgba(7,11,18,0.95)] p-3 text-xs text-[var(--text)]">{task.body}</pre>
            </section>
          </article>
        ) : null}
      </Panel>
    </AppShell>
  );
}
