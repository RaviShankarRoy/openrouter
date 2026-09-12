"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { modelRepository } from "@/repository/model";
import type { Modality } from "@/service/model/model";
import { ModelCard } from "@/api/components/models/ModelCard";
import { ModelFilter } from "@/api/components/models/ModelFilter";
import { Skeleton } from "@/api/ui/skeleton";
import { useDebounce } from "@/service/hooks/use-debounce";

// MK-001..010: marketplace. Phase 2 ranks by usage telemetry.
export default function ModelsPage() {
  const [query, setQuery] = useState("");
  const [modality, setModality] = useState<Modality | "all">("all");
  const debounced = useDebounce(query, 200);

  const { data, isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: () => modelRepository.list(),
    staleTime: 5 * 60_000,
  });

  const filtered = useMemo(() => {
    const all = data ?? [];
    return all.filter((m) => {
      const matchesQuery =
        debounced.length === 0 || m.id.toLowerCase().includes(debounced.toLowerCase());
      const matchesModality = modality === "all" || m.modalities.includes(modality);
      return matchesQuery && matchesModality;
    });
  }, [data, debounced, modality]);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Models</h1>
        <p className="text-sm text-muted-foreground">
          Browse the catalog. Click any model for details and benchmarks.
        </p>
      </div>
      <ModelFilter
        query={query}
        onQueryChange={setQuery}
        modality={modality}
        onModalityChange={setModality}
      />
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((m) => (
            <ModelCard key={m.id} model={m} />
          ))}
        </div>
      )}
    </div>
  );
}
