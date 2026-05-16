import type { Config } from "tailwindcss";

/**
 * Forensic dark theme — derived from specs/phase-3-ui.md UI brief (RECON-C).
 * Instrument, not SaaS: radius 2px, hairline borders, monochrome slate +
 * green(success)/red(divergence). Tokens are CSS vars set in globals.css.
 */
const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        surface: "var(--surface)",
        "surface-raised": "var(--surface-raised)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        foreground: "var(--foreground)",
        muted: "var(--muted)",
        "muted-dim": "var(--muted-dim)",
        success: "var(--success)",
        "success-dim": "var(--success-dim)",
        danger: "var(--danger)",
        "danger-bg": "var(--danger-bg)",
        warning: "var(--warning)",
        ring: "var(--ring)",
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        none: "0px",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        "data-xl": ["28px", { lineHeight: "32px", fontWeight: "600" }],
        h: ["15px", { lineHeight: "20px", fontWeight: "600" }],
        body: ["14px", { lineHeight: "21px", fontWeight: "400" }],
        ts: ["13px", { lineHeight: "18px", fontWeight: "500" }],
        label: ["11px", { lineHeight: "14px", fontWeight: "600" }],
        meta: ["11px", { lineHeight: "14px", fontWeight: "400" }],
      },
    },
  },
  plugins: [],
};

export default config;
