import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        bg: {
          DEFAULT: "#07090d",
          2: "#0e131a",
          3: "#151b24",
        },
        border: "#243041",
        accent: {
          DEFAULT: "#5b9cff",
          green: "#3ecf8e",
          red: "#f07178",
          yellow: "#e6b450",
        },
      },
    },
  },
  plugins: [],
};
export default config;
