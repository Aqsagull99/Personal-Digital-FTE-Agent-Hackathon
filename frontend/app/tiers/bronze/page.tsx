"use client";

import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { TierSelector } from "@/components/tier-selector";
import { WatcherControlBoard } from "@/components/watcher-control-board";

export default function BronzeTierPage(): JSX.Element {
  return (
    <AppShell>
      <Panel title="Bronze Tier" subtitle="Gmail and Filesystem watcher operations" action={<TierSelector />}>
        <WatcherControlBoard requiredTier="bronze" />
      </Panel>
    </AppShell>
  );
}
