import { Suspense } from "react";

import { CreditBalanceCard } from "@/api/components/billing/CreditBalanceCard";
import { UsageChart } from "@/api/layout/UsageChart";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/api/ui/card";
import { Skeleton } from "@/api/ui/skeleton";

// FE-005 dashboard overview. Composed of three independently-streaming RSC
// boundaries via Suspense so a slow query doesn't block the page shell.
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
        <p className="text-sm text-muted-foreground">Usage, spend, and key metrics for the last 30 days.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Suspense fallback={<Skeleton className="h-32" />}>
          <CreditBalanceCard />
        </Suspense>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Requests (30d)</CardTitle>
            <CardDescription>All keys, all models</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">—</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Avg latency</CardTitle>
            <CardDescription>P95 response time</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">—</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Daily usage</CardTitle>
          <CardDescription>Requests and cost over the last 30 days.</CardDescription>
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
