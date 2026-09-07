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
          bg: "#0a0a0f",
          card: "#12121a",
          accent: "#00d4aa",
          muted: "#8b8b9e",
          border: "#1e1e2e",
        },
        ink: {
          950: "#0a0a0f",
          900: "#12121a",
          800: "#12121a",
          700: "#1a1a24",
          600: "#1e1e2e",
        },
      },
      boxShadow: {
        panel: "0 24px 80px rgba(0, 0, 0, 0.45)",
        glass: "0 8px 40px rgba(0, 212, 170, 0.08)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
