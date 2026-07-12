import type { Config } from "tailwindcss";

// Tailwind 4 reads most config from CSS via @theme; this file exists for
// editor tooling and content scanning only.
const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx,mdx}",
    "./src/widgets/**/*.{ts,tsx}",
    "./src/features/**/*.{ts,tsx}",
    "./src/entities/**/*.{ts,tsx}",
    "./src/shared/**/*.{ts,tsx}",
  ],
  darkMode: "class",
};

export default config;
