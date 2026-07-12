"use client";

import { Toaster as SonnerToaster, toast } from "sonner";
import { useTheme } from "next-themes";

// Theme-aware Sonner host. Mount once at the root layout.
export function Toaster() {
  const { resolvedTheme } = useTheme();
  return (
    <SonnerToaster
      theme={(resolvedTheme as "light" | "dark") ?? "system"}
      richColors
      closeButton
      position="top-right"
    />
  );
}

export { toast };
