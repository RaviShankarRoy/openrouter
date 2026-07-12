"""Provider adapter plugin architecture (DRD §7.2).

Adding a new provider:
  1. Create app/infrastructure/providers/{name}.py extending ProviderAdapter
  2. Implement normalize_request, normalize_response, count_tokens, etc.
  3. Register in app/infrastructure/providers/registry.py
  4. Add models to the catalog migration
  5. Set the API key env var
"""
from app.infrastructure.providers.base import (
    HealthStatus,
    PricingTier,
    ProviderAdapter,
    TokenCount,
    UnifiedChunk,
    UnifiedRequest,
    UnifiedResponse,
)
from app.infrastructure.providers.registry import ProviderRegistry

__all__ = [
    "HealthStatus",
    "PricingTier",
    "ProviderAdapter",
    "ProviderRegistry",
    "TokenCount",
    "UnifiedChunk",
    "UnifiedRequest",
    "UnifiedResponse",
]
