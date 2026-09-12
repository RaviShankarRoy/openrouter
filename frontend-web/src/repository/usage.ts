import { apiClient } from "@/repository/client";
import type { UsageSummary, UsageWindow } from "@/service/model/usage";

export const usageRepository = {
  summary: (window: UsageWindow = "month"): Promise<UsageSummary> =>
    apiClient.get<UsageSummary>(`/usage/summary?window=${window}`),
};
