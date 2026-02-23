export type AccessTier = "bronze" | "silver" | "gold";

export type WatcherMeta = {
  name: string;
  label: string;
  tier: AccessTier;
};

export const ACCESS_TIERS: AccessTier[] = ["bronze", "silver", "gold"];

const tierRank: Record<AccessTier, number> = {
  bronze: 1,
  silver: 2,
  gold: 3
};

export const WATCHER_META: WatcherMeta[] = [
  { name: "gmail", label: "Gmail Watcher", tier: "bronze" },
  { name: "filesystem", label: "Filesystem Watcher", tier: "bronze" },
  { name: "whatsapp", label: "WhatsApp Watcher", tier: "silver" },
  { name: "linkedin", label: "LinkedIn Watcher", tier: "silver" },
  { name: "twitter", label: "Twitter Watcher", tier: "silver" },
  { name: "facebook", label: "Facebook Watcher", tier: "gold" },
  { name: "instagram", label: "Instagram Watcher", tier: "gold" }
];

export const TIER_WATCHERS: Record<AccessTier, string[]> = {
  bronze: WATCHER_META.filter((item) => item.tier === "bronze").map((item) => item.name),
  silver: WATCHER_META.filter((item) => item.tier === "bronze" || item.tier === "silver").map((item) => item.name),
  gold: WATCHER_META.map((item) => item.name)
};

export function hasTierAccess(currentTier: AccessTier, requiredTier: AccessTier): boolean {
  return tierRank[currentTier] >= tierRank[requiredTier];
}

export function normalizeWatcherName(name: string): string {
  return name.replace(/_watcher$/i, "").trim().toLowerCase();
}

export function watcherLabel(name: string): string {
  const normalized = normalizeWatcherName(name);
  const found = WATCHER_META.find((item) => item.name === normalized);
  return found?.label ?? normalized.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}
