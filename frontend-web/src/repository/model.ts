import { apiClient } from "@/repository/client";
import type { Model } from "@/service/model/model";

// Wire format snake_cases pricing fields; we normalize to camelCase here so
// the UI layer never branches on transport conventions.
type WireModel = {
  id: string;
  provider: string;
  modalities: Model["modalities"];
  context_window?: number;
  pricing: {
    input_per_million?: number;
    output_per_million?: number;
    cached_input_per_million?: number;
  };
  description?: string;
  quality_score?: number;
  median_latency_ms?: number;
};

function normalize(wire: WireModel): Model {
  return {
    id: wire.id,
    provider: wire.provider,
    modalities: wire.modalities,
    contextWindow: wire.context_window ?? 0,
    pricing: {
      inputPerMillion: wire.pricing.input_per_million ?? 0,
      outputPerMillion: wire.pricing.output_per_million ?? 0,
      ...(wire.pricing.cached_input_per_million !== undefined
        ? { cachedInputPerMillion: wire.pricing.cached_input_per_million }
        : {}),
    },
    ...(wire.description ? { description: wire.description } : {}),
    ...(wire.quality_score !== undefined ? { qualityScore: wire.quality_score } : {}),
    ...(wire.median_latency_ms !== undefined ? { medianLatencyMs: wire.median_latency_ms } : {}),
  };
}

export const modelRepository = {
  async list(): Promise<Model[]> {
    const response = await apiClient.get<{ data: WireModel[] }>("/models");
    return response.data.map(normalize);
  },
  async get(id: string): Promise<Model> {
    const wire = await apiClient.get<WireModel>(`/models/${encodeURIComponent(id)}`);
    return normalize(wire);
  },
};
