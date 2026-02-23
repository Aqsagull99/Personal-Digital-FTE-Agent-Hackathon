"use client";

import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { WatcherControlBoard } from "@/components/watcher-control-board";

export default function WatchersStatusPage(): JSX.Element {
  return (
    <AppShell>
      <Panel title="Watchers Status" subtitle="Unified status board across all configured watchers">
        <WatcherControlBoard requiredTier="gold" />
      </Panel>
    </AppShell>
  );
}
