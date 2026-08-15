/** @type {import('tailwindcss').Config} */

// Every token is `rgb(var(--x) / <alpha-value>)` so opacity modifiers such as
// `bg-brand/40` resolve correctly against the CSS variables in globals.css.
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: token("bg"),
        brand: token("brand"),
        "brand-ink": token("brand-ink"),
        "brand-deep": token("brand-deep"),
        surface: token("surface"),
        "surface-2": token("surface-2"),
        "subtitle-bg": token("subtitle-bg"),
        "subtitle-fg": token("subtitle-fg"),
        muted: token("muted"),
        track: token("track"),
        "track-fill": token("track-fill"),
        accent: token("accent"),
        ink: token("ink"),
      },
      fontFamily: {
        ui: ["var(--font-ui)", "Tahoma", "Arial", "sans-serif"],
        arabic: ["var(--font-arabic)", "Amiri", "serif"],
      },
      borderRadius: {
        card: "1.5rem",
        pill: "9999px",
      },
      boxShadow: {
        card: "0 1px 2px rgb(36 3 10 / 0.04), 0 8px 24px -12px rgb(36 3 10 / 0.12)",
        lift: "0 2px 4px rgb(36 3 10 / 0.05), 0 18px 40px -18px rgb(36 3 10 / 0.28)",
        stage: "0 24px 60px -24px rgb(36 3 10 / 0.55)",
      },
      animation: {
        "cue-in": "cue-in 260ms ease-out",
        rise: "rise 420ms ease-out both",
      },
    },
  },
  plugins: [],
};
