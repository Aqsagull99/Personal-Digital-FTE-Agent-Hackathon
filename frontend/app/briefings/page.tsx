"use client";

import Link from "next/link";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchBriefings } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";

export default function BriefingsPage(): JSX.Element {
  const briefings = useLiveQuery("briefings", fetchBriefings, { refreshInterval: 15000 });

  return (
    <AppShell>
      <Panel
        title="CEO Briefing Viewer"
        subtitle="Navigate weekly briefings from /Briefings"
        action={<button className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm text-white" onClick={() => void briefings.refresh()}>{briefings.loading ? "Loading..." : "Refresh"}</button>}
      >
        {briefings.error ? <p className="mb-3 text-xs text-[var(--bad)]">{briefings.error}</p> : null}
        <div className="space-y-2">
          {(briefings.data ?? []).map((file) => (
            <Link key={file.id} href={`/briefings/${encodeURIComponent(file.id)}`} className="block rounded-xl border border-[var(--line)] bg-[rgba(11,18,32,0.7)] p-3 transition hover:border-[var(--accent)]">
              <p className="text-sm font-semibold text-[var(--text)]">{file.title}</p>
              <p className="mt-1 text-xs text-[var(--muted)]">Week: {file.weekLabel} • Date: {file.date}</p>
              <p className="mt-1 text-xs text-[var(--muted)]">{file.filePath}</p>
            </Link>
          ))}
          {(briefings.data?.length ?? 0) === 0 && !briefings.loading ? <p className="text-sm text-[var(--muted)]">No briefing files found.</p> : null}
        </div>
      </Panel>
    </AppShell>
  );
}
