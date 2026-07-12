import { apiClient } from "@/shared/api/client";
import type { UsageSummary, UsageWindow } from "@/entities/usage/types";

export const usageRepository = {
  summary: (window: UsageWindow = "month"): Promise<UsageSummary> =>
    apiClient.get<UsageSummary>(`/usage/summary?window=${window}`),
};
