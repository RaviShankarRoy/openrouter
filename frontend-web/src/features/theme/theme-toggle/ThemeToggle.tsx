"use client";

import { useTheme } from "next-themes";

import { Button } from "@/shared/ui/button";

// FE-002: dark/light toggle. Uses next-themes for class-based switching.
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      aria-label="Toggle theme"
    >
      {theme === "dark" ? "Light mode" : "Dark mode"}
    </Button>
  );
}
