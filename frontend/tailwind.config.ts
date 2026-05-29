import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f2fbfd",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#ecf5f7",
        "surface-container": "#e6eff1",
        "surface-container-high": "#e1eaec",
        "surface-container-highest": "#dbe4e6",
        "on-surface": "#141d1f",
        "on-surface-variant": "#40484c",
        outline: "#70787d",
        "outline-variant": "#bfc8cd",
        primary: "#004a5f",
        "primary-container": "#09637e",
        "on-primary": "#ffffff",
        secondary: "#006877",
        "secondary-container": "#8debff",
        "on-secondary-container": "#006b7a",
        "status-intact": "#22C55E",
        "status-minor": "#EAB308",
        "status-moderate": "#F59E0B",
        "status-severe": "#EA580C",
        "status-destroyed": "#DC2626",
        "border-muted": "#D1D5DB"
      },
      fontFamily: {
        sans: ["var(--font-hanken)", "Hanken Grotesk", "sans-serif"],
        mono: ["var(--font-jetbrains)", "JetBrains Mono", "monospace"]
      },
      fontSize: {
        "headline-lg": ["28px", { lineHeight: "36px", fontWeight: "700" }],
        "headline-md": ["20px", { lineHeight: "28px", fontWeight: "600" }],
        "headline-sm": ["16px", { lineHeight: "24px", fontWeight: "600" }],
        "body-md": ["14px", { lineHeight: "20px", fontWeight: "400" }],
        "body-sm": ["13px", { lineHeight: "18px", fontWeight: "400" }],
        "label-mono": ["12px", { lineHeight: "16px", fontWeight: "500", letterSpacing: "0.02em" }],
        "stat-value": ["24px", { lineHeight: "32px", fontWeight: "700" }]
      },
      spacing: {
        "panel-width": "360px"
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem"
      },
      boxShadow: {
        panel: "0 4px 12px rgba(0,0,0,0.05)"
      }
    }
  },
  plugins: []
};

export default config;
