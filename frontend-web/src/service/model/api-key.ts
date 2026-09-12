export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  lastUsedAt: string | null;
  createdAt: string;
  expiresAt: string | null;
  revokedAt: string | null;
  scopes: string[];
  monthlyBudgetUsd: number | null;
}

export interface ApiKeyCreatePayload {
  name: string;
  scopes?: string[];
  expiresInDays?: number;
  monthlyBudgetUsd?: number | null;
}

export interface ApiKeyCreateResponse extends ApiKey {
  // Plaintext key, returned exactly once.
  secret: string;
}
