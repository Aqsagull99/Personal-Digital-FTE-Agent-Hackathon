import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        sand: "var(--sand)",
        coral: "var(--coral)",
        mint: "var(--mint)",
        sky: "var(--sky)",
        steel: "var(--steel)"
      },
      boxShadow: {
        card: "0 12px 30px rgba(7, 27, 32, 0.08)",
        panel: "0 18px 44px rgba(7, 27, 32, 0.16)"
      }
    }
  },
  plugins: []
};

export default config;
