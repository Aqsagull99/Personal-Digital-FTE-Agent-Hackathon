"use client";

import { create } from "zustand";
import type { ExecutiveSummary, SystemHealthResponse, SystemMonitor } from "@/lib/types";

type LivePayload = {
  timestamp: string;
  summary: ExecutiveSummary;
  monitor: SystemMonitor;
  health: SystemHealthResponse;
};

type OpsState = {
  wsConnected: boolean;
  lastEventAt?: string;
  liveSummary?: ExecutiveSummary;
  liveMonitor?: SystemMonitor;
  liveHealth?: SystemHealthResponse;
  setConnected: (value: boolean) => void;
  ingest: (payload: LivePayload) => void;
};

export const useOpsStore = create<OpsState>((set) => ({
  wsConnected: false,
  lastEventAt: undefined,
  liveSummary: undefined,
  liveMonitor: undefined,
  liveHealth: undefined,
  setConnected: (value) => set({ wsConnected: value }),
  ingest: (payload) =>
    set({
      wsConnected: true,
      lastEventAt: payload.timestamp,
      liveSummary: payload.summary,
      liveMonitor: payload.monitor,
      liveHealth: payload.health
    })
}));
