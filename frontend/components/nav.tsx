"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bot, CircleDollarSign, FileText, Inbox, LayoutDashboard, Lock, Scale, ShieldAlert, ShieldCheck, ShieldEllipsis, ShieldPlus, SquareKanban, Wallet } from "lucide-react";
import { RoleStatus } from "@/components/role-status";
import { hasTierAccess, type AccessTier } from "@/lib/watcher-tiers";
import { useTier } from "@/lib/use-tier";

const items = [
  { href: "/", label: "Autonomous", icon: LayoutDashboard },
  { href: "/accounting", label: "Accounting", icon: Wallet },
  { href: "/execution", label: "Execution", icon: Bot },
  { href: "/inbox", label: "Needs Action", icon: Inbox },
  { href: "/oversight", label: "Oversight", icon: ShieldAlert },
  { href: "/compliance", label: "Compliance", icon: Scale },
  { href: "/health", label: "System Health", icon: Activity },
  { href: "/briefings", label: "CEO Briefings", icon: FileText },
  { href: "/logs", label: "Raw Logs", icon: CircleDollarSign }
];

const watcherItems = [
  { href: "/watchers-status", label: "Watchers Status", icon: SquareKanban, minTier: "bronze" as AccessTier },
  { href: "/tiers/bronze", label: "Bronze Tier", icon: ShieldCheck, minTier: "bronze" as AccessTier },
  { href: "/tiers/silver", label: "Silver Tier", icon: ShieldEllipsis, minTier: "silver" as AccessTier },
  { href: "/tiers/gold", label: "Gold Tier", icon: ShieldPlus, minTier: "gold" as AccessTier },
  { href: "/dashboard", label: "Watcher Dashboard", icon: SquareKanban, minTier: "bronze" as AccessTier }
];

export function SideNav(): JSX.Element {
  const pathname = usePathname();
  const { tier } = useTier();

  return (
    <aside className="w-full rounded-3xl border border-[var(--line)] bg-[var(--surface-1)] p-4 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur lg:w-72">
      <div className="mb-6 border-b border-[var(--line)] pb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">AI Employee</p>
        <h2 className="mt-2 text-xl font-semibold text-[var(--text)]">Executive Modules</h2>
      </div>
      <nav className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const content = (
            <>
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </>
          );

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`relative flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm ${
                active
                  ? "bg-[color-mix(in_srgb,var(--accent)_16%,transparent)] text-[var(--text)]"
                  : "text-[var(--muted)] hover:bg-[color-mix(in_srgb,var(--accent)_10%,transparent)] hover:text-[var(--text)]"
              }`}
            >
              {active ? <span className="absolute left-1 top-2.5 bottom-2.5 w-1 rounded-full bg-[var(--accent)]" /> : null}
              {content}
            </Link>
          );
        })}
      </nav>
      <div className="my-4 border-t border-[var(--line)] pt-3">
        <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">Watcher Control</p>
        <nav className="space-y-1">
          {watcherItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const locked = !hasTierAccess(tier, item.minTier);
            const content = (
              <>
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
                {locked ? <Lock className="ml-auto h-3.5 w-3.5" /> : null}
              </>
            );

            if (locked) {
              return (
                <div
                  key={item.href}
                  className="flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm text-[var(--muted)] opacity-70"
                  aria-disabled
                >
                  {content}
                </div>
              );
            }

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm ${
                  active
                    ? "bg-[color-mix(in_srgb,var(--accent)_16%,transparent)] text-[var(--text)]"
                    : "text-[var(--muted)] hover:bg-[color-mix(in_srgb,var(--accent)_10%,transparent)] hover:text-[var(--text)]"
                }`}
              >
                {active ? <span className="absolute left-1 top-2.5 bottom-2.5 w-1 rounded-full bg-[var(--accent)]" /> : null}
                {content}
              </Link>
            );
          })}
        </nav>
      </div>
      <RoleStatus />
    </aside>
  );
}
