import Link from "next/link";

import { LoginButton } from "@/features/auth/login-button/LoginButton";
import { ThemeToggle } from "@/features/theme/theme-toggle/ThemeToggle";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

// FE-001 landing page. RSC by default — no client JS shipped except for the
// interactive widgets imported below (LoginButton, ThemeToggle).
const features = [
  {
    title: "OpenAI-compatible",
    body: "Drop-in proxy. Change `base_url`, keep your existing SDK calls.",
  },
  {
    title: "60+ providers",
    body: "Unified surface for OpenAI, Anthropic, Google, xAI, Meta, and more.",
  },
  {
    title: "Smart routing",
    body: "Cost, latency, or quality strategies — selectable per API key.",
  },
  {
    title: "Streaming-first",
    body: "<200ms TTFT, SSE proxy with zero buffering on the hot path.",
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-6xl flex-col px-6 py-8">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <span aria-hidden className="inline-block h-6 w-6 rounded-md bg-primary" />
          OpenRouter
        </div>
        <nav aria-label="Primary" className="flex items-center gap-3">
          <Link href="/models" className="text-sm hover:underline">
            Models
          </Link>
          <Link href="/pricing" className="text-sm hover:underline">
            Pricing
          </Link>
          <Link href="/docs" className="text-sm hover:underline">
            Docs
          </Link>
          <ThemeToggle />
          <LoginButton />
        </nav>
      </header>

      <section className="mt-20 grid gap-8 md:mt-32 md:grid-cols-2 md:items-center">
        <div className="space-y-6">
          <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
            One API for every model that matters.
          </h1>
          <p className="text-lg text-muted-foreground">
            A unified, OpenAI-compatible gateway with cost-aware routing, semantic caching, and
            production-grade observability. Built for teams that ship.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/dashboard">Get started</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/playground">Try the playground</Link>
            </Button>
          </div>
        </div>
        <pre className="overflow-x-auto rounded-lg border bg-muted/40 p-4 text-xs font-mono leading-6">
{`from openai import OpenAI

client = OpenAI(
    base_url="https://api.openrouter.example.com/api/v1",
    api_key="sk-or-v1-...",
)

stream = client.chat.completions.create(
    model="anthropic/claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")`}
        </pre>
      </section>

      <section aria-label="Features" className="mt-24 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((f) => (
          <Card key={f.title}>
            <CardHeader>
              <CardTitle className="text-base">{f.title}</CardTitle>
              <CardDescription>{f.body}</CardDescription>
            </CardHeader>
            <CardContent />
          </Card>
        ))}
      </section>

      <footer className="mt-auto pt-24 text-sm text-muted-foreground">
        <div className="flex flex-wrap items-center justify-between gap-4 border-t pt-6">
          <span>© {new Date().getFullYear()} OpenRouter. All rights reserved.</span>
          <div className="flex gap-4">
            <Link href="/status">Status</Link>
            <Link href="/changelog">Changelog</Link>
            <Link href="/docs">Docs</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
