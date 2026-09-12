"use client";

import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { usageRepository } from "@/repository/usage";
import type { UsageWindow } from "@/service/model/usage";
import { Skeleton } from "@/api/ui/skeleton";

// FE-005: usage chart. Daily series — Recharts handles responsive sizing.
export function UsageChart({ window }: { window: UsageWindow }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["usage", window],
    queryFn: () => usageRepository.summary(window),
  });

  if (isLoading) return <Skeleton className="h-72" />;
  if (error || !data) return <p className="text-sm text-destructive">Failed to load usage.</p>;

  return (
    <ResponsiveContainer width="100%" height={288}>
      <LineChart data={data.series} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis dataKey="date" fontSize={12} stroke="currentColor" />
        <YAxis fontSize={12} stroke="currentColor" />
        <Tooltip
          contentStyle={{
            background: "hsl(var(--background))",
            border: "1px solid hsl(var(--border))",
            borderRadius: 6,
            fontSize: 12,
          }}
        />
        <Line type="monotone" dataKey="requests" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="costUsd" stroke="hsl(var(--destructive))" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
