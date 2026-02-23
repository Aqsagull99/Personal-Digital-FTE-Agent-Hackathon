"use client";

import { useLiveEvents } from "@/lib/use-live-events";

export function LiveEventsBoot(): null {
  useLiveEvents();
  return null;
}
