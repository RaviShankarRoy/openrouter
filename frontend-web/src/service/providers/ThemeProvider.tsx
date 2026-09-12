"use client";

import { ThemeProvider as NextThemesProvider, type ThemeProviderProps } from "next-themes";
import type { ReactNode } from "react";

// FE-002: theme is class-based (`class="dark"`) so Tailwind's `dark:` variants
// flip at the html root.
export function ThemeProvider({
  children,
  ...props
}: { children: ReactNode } & Partial<ThemeProviderProps>) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
