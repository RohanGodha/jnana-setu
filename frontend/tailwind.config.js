/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // 08-FRONTEND-SPEC.md palette
        bg: "#0F0E0B",
        surface: "#1A1916",
        accent: "#C9923A",
        "text-primary": "#F0EDE6",
        "text-secondary": "#8C8880",
        anuyoga: {
          dravyanuyog: "#7C6AE8",
          charananuyog: "#3B9E75",
          prathamanuyoga: "#C97A3A",
          karnanuyoga: "#4A8FC9",
        },
      },
      fontFamily: {
        display: ['"Crimson Pro"', "serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      keyframes: {
        "knowledge-line": {
          "0%": { transform: "scaleX(0)", opacity: "0" },
          "100%": { transform: "scaleX(1)", opacity: "1" },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "knowledge-line": "knowledge-line 1.2s ease-out forwards",
        "fade-in": "fade-in 0.35s ease-out forwards",
      },
    },
  },
  plugins: [],
};
