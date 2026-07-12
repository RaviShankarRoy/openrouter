// Mirrors components/schemas/Model in shared/openapi/openapi.yaml.
// Hand-curated until the OpenAPI codegen lands; once it does, this file should
// re-export the generated type to keep the wire contract source-of-truth.

export type Modality = "text" | "image" | "audio" | "video" | "embedding";

export interface ModelPricing {
  inputPerMillion: number;
  outputPerMillion: number;
  cachedInputPerMillion?: number;
}

export interface Model {
  id: string;
  provider: string;
  modalities: Modality[];
  contextWindow: number;
  pricing: ModelPricing;
  description?: string;
  // Phase 2 — observed quality/latency stats from telemetry.
  qualityScore?: number;
  medianLatencyMs?: number;
}
