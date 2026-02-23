"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchAiLoopStatus, fetchWatchers, processAllNow, processApprovedNow, startAiLoop, startWatcher, stopAiLoop, stopWatcher } from "@/lib/client-api";
import { FeedbackBanner } from "@/components/feedback-banner";
import { useLiveQuery } from "@/lib/use-live-query";

type ActionItem = {
  id: string;
  label: string;
  keywords: string;
  group: "Navigation" | "AI Actions" | "Watchers";
  run: () => Promise<void> | void;
};

export function CommandPalette(): JSX.Element {
  const router = useRouter();
  const watchers = useLiveQuery("palette-watchers", fetchWatchers, { refreshInterval: 12000 });
  const loop = useLiveQuery("palette-loop", fetchAiLoopStatus, { refreshInterval: 7000 });
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKeydown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((prev) => !prev);
      }
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    function openByEvent() {
      setOpen(true);
    }

    window.addEventListener("keydown", onKeydown);
    window.addEventListener("open-command-palette", openByEvent as EventListener);
    return () => {
      window.removeEventListener("keydown", onKeydown);
      window.removeEventListener("open-command-palette", openByEvent as EventListener);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setSelected(0);
    setTimeout(() => inputRef.current?.focus(), 20);
  }, [open]);

  const actions = useMemo<ActionItem[]>(() => {
    const nav = [
      { id: "nav-home", label: "Go: Autonomous Dashboard", keywords: "home dashboard autonomous", path: "/" },
      { id: "nav-inbox", label: "Go: Needs Action", keywords: "inbox needs action tasks", path: "/inbox" },
      { id: "nav-approvals", label: "Go: Oversight / Approvals", keywords: "approval oversight pending", path: "/oversight" },
      { id: "nav-watchers", label: "Go: Watchers Status", keywords: "watchers status monitor", path: "/watchers-status" },
      { id: "nav-logs", label: "Go: Logs", keywords: "logs audit", path: "/logs" }
    ].map<ActionItem>((item) => ({
      id: item.id,
      label: item.label,
      keywords: item.keywords,
      group: "Navigation",
      run: () => {
        router.push(item.path);
        setOpen(false);
      }
    }));

    const ops: ActionItem[] = [
      {
        id: "op-loop-start",
        label: "Action: Start AI Loop",
        keywords: "start ai loop process",
        group: "AI Actions",
        run: async () => {
          const res = await startAiLoop();
          setMessage(res.message);
          await loop.refresh();
        }
      },
      {
        id: "op-loop-stop",
        label: "Action: Stop AI Loop",
        keywords: "stop ai loop",
        group: "AI Actions",
        run: async () => {
          const res = await stopAiLoop();
          setMessage(res.message);
          await loop.refresh();
        }
      },
      {
        id: "op-process-approved",
        label: "Action: Process Approved",
        keywords: "process approved execute approvals",
        group: "AI Actions",
        run: async () => {
          const res = await processApprovedNow();
          setMessage(res.message);
        }
      },
      {
        id: "op-process-all",
        label: "Action: Process All",
        keywords: "process all approved rejected",
        group: "AI Actions",
        run: async () => {
          const res = await processAllNow();
          setMessage(res.message);
        }
      }
    ];

    const watcherOps =
      watchers.data?.map<ActionItem>((watcher) => {
        const runLabel = watcher.running ? `Action: Stop Watcher (${watcher.name})` : `Action: Start Watcher (${watcher.name})`;
        return {
          id: `watcher-${watcher.name}-${watcher.running ? "stop" : "start"}`,
          label: runLabel,
          keywords: `watcher ${watcher.name} ${watcher.running ? "stop" : "start"}`,
          group: "Watchers",
          run: async () => {
            const res = watcher.running ? await stopWatcher(watcher.name) : await startWatcher(watcher.name);
            setMessage(res.message);
            await watchers.refresh();
          }
        };
      }) ?? [];

    return [...nav, ...ops, ...watcherOps];
  }, [loop, router, watchers]);

  function fuzzyScore(text: string, q: string): number {
    if (!q) return 1;
    const hay = text.toLowerCase();
    const needle = q.toLowerCase();
    if (hay.includes(needle)) return 100 - (hay.indexOf(needle) / 10);
    let score = 0;
    let idx = 0;
    for (const ch of needle) {
      const found = hay.indexOf(ch, idx);
      if (found === -1) return -1;
      score += 1;
      idx = found + 1;
    }
    return score;
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return actions;
    return actions
      .map((item) => {
        const base = `${item.label} ${item.keywords}`;
        const score = fuzzyScore(base, q);
        return { item, score };
      })
      .filter((entry) => entry.score >= 0)
      .sort((a, b) => b.score - a.score)
      .map((entry) => entry.item);
  }, [actions, query]);

  const grouped = useMemo(() => {
    const map: Record<ActionItem["group"], ActionItem[]> = {
      Navigation: [],
      "AI Actions": [],
      Watchers: []
    };
    for (const item of filtered) map[item.group].push(item);
    return map;
  }, [filtered]);

  useEffect(() => {
    if (selected >= filtered.length) {
      setSelected(Math.max(0, filtered.length - 1));
    }
  }, [filtered.length, selected]);

  async function runSelected(index: number): Promise<void> {
    const item = filtered[index];
    if (!item) return;
    setBusy(true);
    setError(null);
    try {
      await item.run();
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  if (!open) return <></>;

  return (
    <div className="fixed inset-0 z-50 bg-[rgba(2,8,22,0.45)] p-4 backdrop-blur-sm" onClick={() => setOpen(false)}>
      <div
        className="mx-auto mt-12 w-full max-w-2xl rounded-2xl border border-[var(--line)] bg-[var(--surface-1)] shadow-[0_24px_60px_rgba(2,8,22,0.35)]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="border-b border-[var(--line)] px-4 py-3">
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setSelected((prev) => Math.min(prev + 1, filtered.length - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setSelected((prev) => Math.max(prev - 1, 0));
              } else if (event.key === "Enter") {
                event.preventDefault();
                void runSelected(selected);
              }
            }}
            placeholder="Type a command... (navigation, loop, watchers)"
            className="w-full rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] outline-none"
          />
        </div>

        <div className="max-h-[360px] overflow-auto p-2">
          {(["Navigation", "AI Actions", "Watchers"] as const).map((groupName) => (
            grouped[groupName].length > 0 ? (
              <div key={groupName} className="mb-2">
                <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">{groupName}</p>
                {grouped[groupName].map((item) => {
                  const index = filtered.findIndex((it) => it.id === item.id);
                  return (
                    <button
                      type="button"
                      key={item.id}
                      disabled={busy}
                      onClick={() => void runSelected(index)}
                      className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm ${
                        selected === index
                          ? "bg-[color-mix(in_srgb,var(--accent)_18%,transparent)] text-[var(--text)]"
                          : "text-[var(--muted)] hover:bg-[color-mix(in_srgb,var(--accent)_10%,transparent)] hover:text-[var(--text)]"
                      }`}
                    >
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            ) : null
          ))}
          {filtered.length === 0 ? <p className="px-3 py-2 text-sm text-[var(--muted)]">No commands match.</p> : null}
        </div>

        <div className="border-t border-[var(--line)] p-3">
          {message ? <FeedbackBanner tone="success" message={message} /> : null}
          {error ? <FeedbackBanner tone="error" message={error} /> : null}
          <p className="mt-2 text-[11px] text-[var(--muted)]">Use ↑ ↓ and Enter • Close with Esc • Open with Ctrl/Cmd + K</p>
        </div>
      </div>
    </div>
  );
}
