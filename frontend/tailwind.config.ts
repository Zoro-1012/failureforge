import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        forge: {
          bg: "#0b0f17",
          panel: "#131a26",
          border: "#1e2a3c",
          accent: "#3b82f6",
        },
      },
    },
  },
  plugins: [],
};

export default config;
