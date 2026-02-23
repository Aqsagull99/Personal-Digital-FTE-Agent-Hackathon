"use client";

import { useEffect } from "react";
import { API_BASE_URL } from "@/lib/runtime";
import { useOpsStore } from "@/lib/ops-store";

function wsUrlFromApiBase(apiBase: string): string {
  const url = new URL(apiBase);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${url.host}/ws/events`;
}

export function useLiveEvents(): void {
  const ingest = useOpsStore((s) => s.ingest);
  const setConnected = useOpsStore((s) => s.setConnected);

  useEffect(() => {
    const wsUrl = wsUrlFromApiBase(API_BASE_URL);
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;

    const connect = () => {
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        setConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            timestamp: string;
            summary: any;
            monitor: any;
            health: any;
          };
          ingest(payload as any);
        } catch {
          // ignore malformed payloads
        }
      };

      socket.onclose = () => {
        setConnected(false);
        reconnectTimer = window.setTimeout(connect, 2500);
      };

      socket.onerror = () => {
        setConnected(false);
      };
    };

    connect();

    return () => {
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (socket && socket.readyState <= WebSocket.OPEN) socket.close();
    };
  }, [ingest, setConnected]);
}
