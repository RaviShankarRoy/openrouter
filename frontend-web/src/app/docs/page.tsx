import type { Metadata } from "next";
import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

export const metadata: Metadata = {
  title: "Documentation",
};

// FE-015: docs index. Real content lives in /content/docs and is rendered via
// the [...slug] route below. This page is the index hub.
const sections = [
  { slug: "quickstart", title: "Quickstart", body: "Send your first chat completion in under five minutes." },
  { slug: "authentication", title: "Authentication", body: "API keys, OAuth, and provisioning tokens." },
  { slug: "streaming", title: "Streaming", body: "Server-Sent Events and incremental UI patterns." },
  { slug: "routing", title: "Routing strategies", body: "Cost, latency, quality, and geo strategies." },
  { slug: "errors", title: "Errors", body: "OpenAI-compatible error envelope and retry semantics." },
  { slug: "openapi", title: "OpenAPI reference", body: "Generated reference from the canonical spec." },
];

export default function DocsIndexPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <h1 className="mb-8 text-3xl font-semibold tracking-tight">Documentation</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {sections.map((s) => (
          <Link key={s.slug} href={`/docs/${s.slug}`} className="block focus:outline-none">
            <Card className="h-full transition-colors hover:border-primary">
              <CardHeader>
                <CardTitle className="text-base">{s.title}</CardTitle>
                <CardDescription>{s.body}</CardDescription>
              </CardHeader>
              <CardContent />
            </Card>
          </Link>
        ))}
      </div>
    </main>
  );
}
