export function FeedbackBanner({
  tone,
  message
}: {
  tone: "success" | "error" | "info" | "warn";
  message: string;
}): JSX.Element {
  const tones: Record<typeof tone, string> = {
    success: "border-[color-mix(in_srgb,var(--ok)_45%,transparent)] bg-[color-mix(in_srgb,var(--ok)_16%,transparent)] text-[var(--ok)]",
    error: "border-[color-mix(in_srgb,var(--bad)_45%,transparent)] bg-[color-mix(in_srgb,var(--bad)_14%,transparent)] text-[var(--bad)]",
    info: "border-[color-mix(in_srgb,var(--accent)_40%,transparent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--text)]",
    warn: "border-[color-mix(in_srgb,var(--warn)_42%,transparent)] bg-[color-mix(in_srgb,var(--warn)_16%,transparent)] text-[var(--warn)]"
  };

  return <p className={`rounded-lg border px-3 py-2 text-xs ${tones[tone]}`}>{message}</p>;
}
