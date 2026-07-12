export type UsageWindow = "day" | "week" | "month";

export interface UsageDailyPoint {
  date: string;
  promptTokens: number;
  completionTokens: number;
  requests: number;
  costUsd: number;
}

export interface UsageSummary {
  window: UsageWindow;
  totalRequests: number;
  totalTokens: number;
  totalCostUsd: number;
  series: UsageDailyPoint[];
  byModel: Array<{
    modelId: string;
    requests: number;
    tokens: number;
    costUsd: number;
  }>;
}
