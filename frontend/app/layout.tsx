import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";
import "@/app/globals.css";
import { LiveEventsBoot } from "@/components/live-events-boot";
import { ThemeProvider } from "@/components/theme-provider";

const spaceGrotesk = Space_Grotesk({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Employee Operations Console",
  description: "Control center for the Personal AI Employee workflow"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>): JSX.Element {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var key = 'ai_employee_theme';
                  var stored = localStorage.getItem(key);
                  var dark = stored ? stored === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
                  var root = document.documentElement;
                  if (dark) root.classList.add('dark');
                  else root.classList.remove('dark');
                  root.style.colorScheme = dark ? 'dark' : 'light';
                } catch (e) {}
              })();
            `
          }}
        />
      </head>
      <body className={spaceGrotesk.className}>
        <ThemeProvider>
          <LiveEventsBoot />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
