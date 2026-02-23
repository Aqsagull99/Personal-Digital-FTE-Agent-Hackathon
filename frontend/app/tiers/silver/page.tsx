"use client";

import { AppShell } from "@/components/shell";
import { Panel } from "@/components/panel";
import { TierSelector } from "@/components/tier-selector";
import { WatcherControlBoard } from "@/components/watcher-control-board";

export default function SilverTierPage(): JSX.Element {
  return (
    <AppShell>
      <Panel title="Silver Tier" subtitle="Bronze + WhatsApp, LinkedIn, Twitter watchers" action={<TierSelector />}>
        <WatcherControlBoard requiredTier="silver" />
      </Panel>
    </AppShell>
  );
}
