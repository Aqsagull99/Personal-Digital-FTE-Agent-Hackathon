"use client";

import { useState } from "react";
import { FileEdit, Loader2 } from "lucide-react";
import { FeedbackBanner } from "@/components/feedback-banner";
import { Panel } from "@/components/panel";
import { createEmailDraft, fetchDraftHistory, requestEmailApproval } from "@/lib/client-api";
import { useLiveQuery } from "@/lib/use-live-query";
import { formatDateTime } from "@/lib/utils";

export function CreateDraftPanel(): JSX.Element {
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState<"draft" | "approval" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const history = useLiveQuery("draft-history", () => fetchDraftHistory(8), { refreshInterval: 8000 });

  function validate(): boolean {
    if (!to.trim() || !subject.trim() || !body.trim()) {
      setError("To, subject, and body are required.");
      return false;
    }
    return true;
  }

  async function onCreateDraft(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validate()) return;

    setLoading("draft");
    setMessage(null);
    setError(null);
    try {
      const res = await createEmailDraft({
        to: to.trim(),
        subject: subject.trim(),
        body: body.trim()
      });
      setMessage(res.message);
      await history.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Draft creation failed");
    } finally {
      setLoading(null);
    }
  }

  async function onSendForApproval() {
    if (!validate()) return;

    setLoading("approval");
    setMessage(null);
    setError(null);
    try {
      const res = await requestEmailApproval({
        to: to.trim(),
        subject: subject.trim(),
        body: body.trim()
      });
      setMessage(res.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create approval");
    } finally {
      setLoading(null);
    }
  }

  return (
    <Panel title="Create Gmail Draft" subtitle="Test email draft creation from the frontend console">
      <form onSubmit={(event) => void onCreateDraft(event)} className="space-y-3">
        <input
          type="email"
          value={to}
          onChange={(event) => setTo(event.target.value)}
          placeholder="Recipient email"
          className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--muted)]"
        />
        <input
          type="text"
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          placeholder="Draft subject"
          className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--muted)]"
        />
        <textarea
          value={body}
          onChange={(event) => setBody(event.target.value)}
          rows={4}
          placeholder="Draft body..."
          className="w-full rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--muted)]"
        />
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="submit"
            disabled={loading !== null}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading === "draft" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileEdit className="h-4 w-4" />}
            {loading === "draft" ? "Creating..." : "Create Draft"}
          </button>
          <button
            type="button"
            onClick={() => void onSendForApproval()}
            disabled={loading !== null}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-4 py-2 text-sm font-medium text-[var(--text)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading === "approval" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileEdit className="h-4 w-4" />}
            {loading === "approval" ? "Submitting..." : "Send For Approval"}
          </button>
        </div>
        {message ? <FeedbackBanner tone="success" message={message} /> : null}
        {error ? <FeedbackBanner tone="error" message={error} /> : null}
      </form>
      <div className="mt-4 border-t border-[var(--line)] pt-3">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Recent Drafts</p>
        <div className="mt-2 space-y-2">
          {(history.data ?? []).map((item) => (
            <div key={`${item.timestamp}-${item.draftId ?? item.subject}`} className="rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2">
              <p className="text-xs text-[var(--text)]">{item.subject}</p>
              <p className="text-[11px] text-[var(--muted)]">{item.to} • {formatDateTime(item.timestamp)}</p>
            </div>
          ))}
          {!history.loading && (history.data?.length ?? 0) === 0 ? <p className="text-xs text-[var(--muted)]">No drafts yet.</p> : null}
        </div>
      </div>
    </Panel>
  );
}
