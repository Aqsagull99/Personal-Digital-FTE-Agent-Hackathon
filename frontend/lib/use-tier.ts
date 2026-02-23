"use client";

import { useCallback, useEffect, useState } from "react";
import { type AccessTier } from "@/lib/watcher-tiers";

const TIER_KEY = "ae_access_tier";
const TIER_EVENT = "ae-tier-change";

function isTier(value: string | null): value is AccessTier {
  return value === "bronze" || value === "silver" || value === "gold";
}

export function useTier(defaultTier: AccessTier = "bronze") {
  const [tier, setTierState] = useState<AccessTier>(defaultTier);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(TIER_KEY);
      if (isTier(stored)) {
        setTierState(stored);
      }
    } catch {
      // ignore storage errors in restricted browsers
    }
  }, []);

  useEffect(() => {
    function syncFromStorage() {
      try {
        const stored = localStorage.getItem(TIER_KEY);
        if (isTier(stored)) {
          setTierState(stored);
        }
      } catch {
        // ignore storage errors in restricted browsers
      }
    }

    function onStorage(event: StorageEvent) {
      if (!event.key || event.key === TIER_KEY) {
        syncFromStorage();
      }
    }

    window.addEventListener("storage", onStorage);
    window.addEventListener(TIER_EVENT, syncFromStorage);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener(TIER_EVENT, syncFromStorage);
    };
  }, []);

  const setTier = useCallback((nextTier: AccessTier) => {
    setTierState(nextTier);
    try {
      localStorage.setItem(TIER_KEY, nextTier);
      window.dispatchEvent(new Event(TIER_EVENT));
    } catch {
      // ignore storage errors in restricted browsers
    }
  }, []);

  return { tier, setTier };
}
