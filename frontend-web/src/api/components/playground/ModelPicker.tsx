"use client";

import { useQuery } from "@tanstack/react-query";

import { modelRepository } from "@/repository/model";
import { Card, CardContent, CardHeader, CardTitle } from "@/api/ui/card";
import { Skeleton } from "@/api/ui/skeleton";

export function ModelPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: () => modelRepository.list(),
    staleTime: 5 * 60_000,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Model</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-9" />
        ) : (
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full rounded border bg-background px-3 py-2 text-sm"
            aria-label="Select model"
          >
            {data?.map((m) => (
              <option key={m.id} value={m.id}>
                {m.id}
              </option>
            ))}
          </select>
        )}
      </CardContent>
    </Card>
  );
}
