import { apiClient } from "@/shared/api/client";
import type { ApiKey, ApiKeyCreatePayload, ApiKeyCreateResponse } from "@/entities/api-key/types";

// FE-004: backs the dashboard API key UI.
export const apiKeyRepository = {
  list: (): Promise<{ data: ApiKey[] }> => apiClient.get<{ data: ApiKey[] }>("/keys"),
  create: (payload: ApiKeyCreatePayload): Promise<ApiKeyCreateResponse> =>
    apiClient.post<ApiKeyCreateResponse>("/keys", payload),
  revoke: (id: string): Promise<void> => apiClient.delete<void>(`/keys/${encodeURIComponent(id)}`),
};
