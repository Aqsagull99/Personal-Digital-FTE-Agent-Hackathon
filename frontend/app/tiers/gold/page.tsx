"use client";

import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { TierSelector } from "@/components/tier-selector";
import { WatcherControlBoard } from "@/components/watcher-control-board";

export default function GoldTierPage(): JSX.Element {
  return (
    <AppShell>
      <Panel title="Gold Tier" subtitle="All watchers including Facebook and Instagram" action={<TierSelector />}>
        <WatcherControlBoard requiredTier="gold" />
      </Panel>
    </AppShell>
  );
}
