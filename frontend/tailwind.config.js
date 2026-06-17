/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#090912",
        "base-secondary": "#0d0d18",
        surface: "#111120",
        "surface-hover": "#161628",
        "surface-active": "#1c1c38",
        accent: "#6366f1",
        "accent-dim": "rgba(99,102,241,0.12)",
        "accent-glow": "rgba(99,102,241,0.25)",
        violet: "#8b5cf6",
        "border-subtle": "rgba(255,255,255,0.06)",
        "border-default": "rgba(255,255,255,0.09)",
        "border-strong": "rgba(255,255,255,0.14)",
        "text-primary": "#e8e8f0",
        "text-secondary": "#8a8aaa",
        "text-muted": "#4a4a68",
        "green-bright": "#22c55e",
        "red-bright": "#ef4444",
        "amber-bright": "#f59e0b",
        "orange-bright": "#f97316",
      },
      fontFamily: {
        display: ["Syne", "sans-serif"],
        sans: ["DM Sans", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        glow: {
          "0%, 100%": { boxShadow: "0 0 8px rgba(99,102,241,0.3)" },
          "50%": { boxShadow: "0 0 20px rgba(99,102,241,0.6)" },
        },
      },
      animation: {
        "fade-up": "fadeUp 0.4s ease both",
        "pulse-dot": "pulseDot 1.4s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
        glow: "glow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
