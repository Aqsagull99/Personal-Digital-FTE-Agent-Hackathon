import { LucideIcon } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

export function StatCard({
  label,
  value,
  note,
  icon: Icon,
  sparkline
}: {
  label: string;
  value: string;
  note: string;
  icon: LucideIcon;
  sparkline?: number[];
}): JSX.Element {
  const sparkData = (sparkline ?? []).map((v, i) => ({ i, v }));

  return (
    <article className="group relative overflow-hidden rounded-3xl border border-[var(--line)] bg-[var(--surface-2)] p-5 shadow-[0_8px_20px_rgba(15,23,42,0.06)] hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(15,23,42,0.1)]">
      <span className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-[color-mix(in_srgb,var(--accent)_55%,transparent)] via-[color-mix(in_srgb,var(--ok)_45%,transparent)] to-transparent" />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">{label}</p>
          <p className="mt-2 text-3xl font-semibold text-[var(--text)]">{value}</p>
          <p className="mt-2 text-sm text-[var(--muted)]">{note}</p>
        </div>
        <span className="rounded-xl bg-[color-mix(in_srgb,var(--accent)_18%,transparent)] p-2 text-[var(--text)] group-hover:scale-105">
          <Icon className="h-5 w-5" />
        </span>
      </div>
      {sparkData.length > 1 ? (
        <div className="mt-3 h-10 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData}>
              <Area type="monotone" dataKey="v" stroke="var(--accent)" strokeWidth={2} fill="color-mix(in_srgb,var(--accent)_18%,transparent)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : null}
    </article>
  );
}
