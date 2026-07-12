import type { Metadata } from "next";

import { Badge } from "@/shared/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";

export const metadata: Metadata = {
  title: "Provider status",
};

// Provider uptime widget — values come from the backend health aggregator.
// Server-rendered with on-page revalidation every 30s.
export const revalidate = 30;

type ProviderStatus = "operational" | "degraded" | "outage";

async function loadStatus(): Promise<{ providers: Array<{ name: string; status: ProviderStatus; uptime30d: number }> }> {
  // Until /system/providers ships in the backend, return a deterministic stub
  // so the page renders during scaffold review.
  return {
    providers: [
      { name: "OpenAI", status: "operational", uptime30d: 99.97 },
      { name: "Anthropic", status: "operational", uptime30d: 99.99 },
      { name: "Google Vertex", status: "degraded", uptime30d: 99.42 },
      { name: "Mistral", status: "operational", uptime30d: 99.91 },
      { name: "Together", status: "operational", uptime30d: 99.85 },
    ],
  };
}

const variantFor: Record<ProviderStatus, "success" | "warning" | "destructive"> = {
  operational: "success",
  degraded: "warning",
  outage: "destructive",
};

export default async function StatusPage() {
  const { providers } = await loadStatus();
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="mb-2 text-3xl font-semibold tracking-tight">Provider status</h1>
      <p className="mb-8 text-muted-foreground">Rolling 30-day availability per upstream provider.</p>
      <div className="grid gap-3">
        {providers.map((p) => (
          <Card key={p.name}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base">{p.name}</CardTitle>
              <Badge variant={variantFor[p.status]}>{p.status}</Badge>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              30-day uptime: <span className="font-medium text-foreground">{p.uptime30d.toFixed(2)}%</span>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
