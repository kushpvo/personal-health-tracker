import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        optimal: "#22c55e",
        sufficient: "#06b6d4",
        out_of_range: "#f97316",
      },
    },
  },
  plugins: [],
} satisfies Config;
