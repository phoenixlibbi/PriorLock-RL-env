import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ["'SF Mono'", "'Fira Code'", "'Cascadia Code'", "monospace"],
      },
      colors: {
        bg: {
          DEFAULT: "#0d1117",
          2: "#161b22",
          3: "#1c2128",
        },
        border: "#30363d",
        accent: {
          DEFAULT: "#58a6ff",
          green: "#3fb950",
          red: "#f85149",
          yellow: "#d29922",
        },
      },
    },
  },
  plugins: [],
};
export default config;
