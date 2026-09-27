import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)",
        brand: "rgb(var(--brand) / <alpha-value>)",
        "brand-deep": "#6B7F78",
        ink: "#1A1A1A",
        surface: "rgb(var(--surface) / <alpha-value>)",
      },
      boxShadow: {
        card: "0 1px 3px rgb(0 0 0 / 0.06), 0 8px 24px rgb(0 0 0 / 0.04)",
      },
    },
  },
  plugins: [],
};

export default config;
