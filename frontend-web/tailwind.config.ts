import type { Config } from "tailwindcss";

// Tailwind 4 reads most config from CSS via @theme; this file exists for
// editor tooling and content scanning only.
const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx,mdx}",
    "./src/api/**/*.{ts,tsx}",
    "./src/service/**/*.{ts,tsx}",
    "./src/repository/**/*.{ts,tsx}",
    "./src/shared/**/*.{ts,tsx}",
  ],
  darkMode: "class",
};

export default config;
