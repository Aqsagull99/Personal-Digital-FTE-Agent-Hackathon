"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { fetchBriefingDetail, fetchBriefings } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";

export default function BriefingDetailPage(): JSX.Element {
  const params = useParams<{ id: string }>();
  const briefingId = Array.isArray(params.id) ? params.id[0] : params.id;

  const detail = useLiveQuery(`briefing-${briefingId}`, () => fetchBriefingDetail(briefingId), { refreshInterval: 15000 });
  const list = useLiveQuery("briefings-index", fetchBriefings, { refreshInterval: 15000 });

  const neighbors = useMemo(() => {
    const items = list.data ?? [];
    const idx = items.findIndex((x) => x.id === briefingId);
    return {
      newer: idx > 0 ? items[idx - 1] : null,
      older: idx >= 0 && idx < items.length - 1 ? items[idx + 1] : null
    };
  }, [list.data, briefingId]);

  return (
    <AppShell>
      <Panel
        title={detail.data?.title ?? "Briefing"}
        subtitle={detail.data ? `Week ${detail.data.weekLabel} • ${detail.data.date}` : "Loading briefing"}
        action={
          <div className="flex gap-2">
            <Link href="/briefings" className="rounded-lg bg-[color-mix(in_srgb,var(--accent)_20%,transparent)] px-3 py-1.5 text-sm text-[var(--text)]">All Briefings</Link>
            {neighbors.newer ? <Link href={`/briefings/${encodeURIComponent(neighbors.newer.id)}`} className="rounded-lg bg-[rgba(17,154,111,0.2)] px-3 py-1.5 text-sm text-[var(--text)]">Newer</Link> : null}
            {neighbors.older ? <Link href={`/briefings/${encodeURIComponent(neighbors.older.id)}`} className="rounded-lg bg-[rgba(183,121,31,0.2)] px-3 py-1.5 text-sm text-[var(--text)]">Older</Link> : null}
          </div>
        }
      >
        {detail.error ? <p className="mb-3 text-xs text-[var(--bad)]">{detail.error}</p> : null}
        {detail.data ? (
          <article className="markdown-body rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-5">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{detail.data.markdown}</ReactMarkdown>
          </article>
        ) : null}
      </Panel>
    </AppShell>
  );
}
