import { SideNav } from "@/components/nav";
import { AppHeader } from "@/components/app-header";
import { CommandPalette } from "@/components/command-palette";

export function AppShell({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <div className="mx-auto min-h-screen max-w-7xl px-4 py-6 lg:px-8 lg:py-8">
      <AppHeader />
      <CommandPalette />
      <div className="grid gap-6 lg:grid-cols-[288px_minmax(0,1fr)]">
        <SideNav />
        <main className="space-y-5">{children}</main>
      </div>
    </div>
  );
}
