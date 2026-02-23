export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(iso));
}

export function priorityTone(priority: "low" | "medium" | "high"): string {
  if (priority === "high") return "bg-[rgba(255,109,122,0.2)] text-[var(--bad)] border-[rgba(255,109,122,0.4)]";
  if (priority === "medium") return "bg-[rgba(241,180,89,0.2)] text-[var(--warn)] border-[rgba(241,180,89,0.4)]";
  return "bg-[rgba(39,209,154,0.2)] text-[var(--ok)] border-[rgba(39,209,154,0.4)]";
}

export function healthTone(status: "healthy" | "degraded" | "offline"): string {
  if (status === "healthy") return "bg-[rgba(39,209,154,0.2)] text-[var(--ok)]";
  if (status === "degraded") return "bg-[rgba(241,180,89,0.2)] text-[var(--warn)]";
  return "bg-[rgba(255,109,122,0.2)] text-[var(--bad)]";
}
