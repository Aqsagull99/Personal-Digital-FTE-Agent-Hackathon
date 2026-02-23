"use client";

import { ACCESS_TIERS, type AccessTier } from "@/lib/watcher-tiers";
import { useTier } from "@/lib/use-tier";

const LABELS: Record<AccessTier, string> = {
  bronze: "Bronze",
  silver: "Silver",
  gold: "Gold"
};

export function TierSelector(): JSX.Element {
  const { tier, setTier } = useTier();

  return (
    <div className="inline-flex rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-1">
      {ACCESS_TIERS.map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => setTier(item)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
            tier === item
              ? "bg-[var(--accent)] text-white"
              : "text-[var(--muted)] hover:bg-[color-mix(in_srgb,var(--accent)_14%,transparent)]"
          }`}
        >
          {LABELS[item]}
        </button>
      ))}
    </div>
  );
}
