import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/service/providers/AuthProvider";
import { QueryProvider } from "@/service/providers/QueryProvider";
import { ThemeProvider } from "@/service/providers/ThemeProvider";
import { Toaster } from "@/api/ui/toast";

import "./globals.css";

// FE-001: viewport set so the responsive grid behaves on mobile.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1120" },
  ],
};

export const metadata: Metadata = {
  title: { default: "OpenRouter — Unified AI Gateway", template: "%s · OpenRouter" },
  description:
    "OpenAI-compatible gateway in front of every major LLM provider. Streaming, observability, and cost controls included.",
  applicationName: "OpenRouter",
  metadataBase: new URL("https://openrouter.example.com"),
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-dvh bg-background font-sans text-foreground antialiased">
        <ThemeProvider>
          <AuthProvider>
            <QueryProvider>
              {children}
              <Toaster />
            </QueryProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
