"use client";

import { useState } from "react";
import { Loader2, PlayCircle } from "lucide-react";
import { FeedbackBanner } from "@/components/feedback-banner";
import { Panel } from "@/components/panel";
import { runAiTask } from "@/lib/client-api";

export function RunAiTaskPanel(): JSX.Element {
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [priority, setPriority] = useState<"low" | "medium" | "high">("medium");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim()) {
      setError("Task prompt is required.");
      return;
    }

    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const response = await runAiTask({
        title: title.trim() || undefined,
        prompt: prompt.trim(),
        priority,
        source: "frontend_console"
      });
      setMessage(response.message + (response.toPath ? ` • ${response.toPath}` : ""));
      setPrompt("");
      setTitle("");
      setPriority("medium");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to queue task");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Panel title="Run AI Task" subtitle="Queue a task for the AI Employee directly from the control center">
      <form onSubmit={(event) => void onSubmit(event)} className="space-y-3">
        <input
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Task title (optional)"
          className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--muted)]"
        />
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Example: Check pending finance approvals and draft responses for high priority clients."
          rows={4}
          className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--muted)]"
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <select
            value={priority}
            onChange={(event) => setPriority(event.target.value as "low" | "medium" | "high")}
            className="rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)]"
          >
            <option value="low">Low priority</option>
            <option value="medium">Medium priority</option>
            <option value="high">High priority</option>
          </select>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlayCircle className="h-4 w-4" />}
            {loading ? "Queueing..." : "Run Task"}
          </button>
        </div>
        {message ? <FeedbackBanner tone="success" message={message} /> : null}
        {error ? <FeedbackBanner tone="error" message={error} /> : null}
      </form>
    </Panel>
  );
}
