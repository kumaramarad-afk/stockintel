import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        gsr: {
          bg: "#020617",
          card: "#0f172a",
          accent: "#10b981",
          muted: "#94a3b8",
          border: "#1e293b",
        },
        ink: {
          950: "#020617",
          900: "#0f172a",
          800: "#0f172a",
          700: "#1e293b",
          600: "#334155",
        },
      },
      boxShadow: {
        panel: "0 24px 80px rgba(0, 0, 0, 0.45)",
        glass: "0 8px 40px rgba(16, 185, 129, 0.08)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
      },
      keyframes: {
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
      animation: {
        marquee: "marquee 38s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
