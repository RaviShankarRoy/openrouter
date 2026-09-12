import type { Metadata } from "next";
import { Suspense } from "react";

import { UsageChart } from "@/api/layout/UsageChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/api/ui/card";
import { Skeleton } from "@/api/ui/skeleton";

export const metadata: Metadata = { title: "Usage" };

export default function UsagePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Usage</h1>
        <p className="text-sm text-muted-foreground">Tokens, requests, and cost across all keys.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>30-day series</CardTitle>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<Skeleton className="h-72" />}>
            <UsageChart window="month" />
          </Suspense>
        </CardContent>
      </Card>
    </div>
  );
}
