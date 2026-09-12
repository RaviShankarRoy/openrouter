"""Gemma 4 adapter — served via Fireworks (OpenAI-compatible).

Apache 2.0 weights. Multimodal: text/image/audio/video + native tool calling.
Pricing here is the in-process bootstrap source; production reads model_pricing
table via PricingRepository.
"""
from __future__ import annotations

from decimal import Decimal

from app.repository.providers.base import PricingTier
from app.repository.providers.openai_adapter import OpenAIAdapter

# Phase-1 catalog. Production loads from the model_pricing table.
_PRICING: dict[str, PricingTier] = {
    "google/gemma-4-31b": PricingTier(
        input_per_million=Decimal("0.30"),
        output_per_million=Decimal("0.50"),
    ),
    "google/gemma-4-26b-moe": PricingTier(
        input_per_million=Decimal("0.20"),
        output_per_million=Decimal("0.40"),
    ),
    "google/gemma-4-e4b": PricingTier(
        input_per_million=Decimal("0.05"),
        output_per_million=Decimal("0.10"),
    ),
    "google/gemma-4-e2b": PricingTier(
        input_per_million=Decimal("0.02"),
        output_per_million=Decimal("0.05"),
    ),
}


class GemmaAdapter(OpenAIAdapter):
    _provider_name = "gemma"
    _base_url = "https://api.fireworks.ai/inference/v1"
    _api_key_setting = "fireworks_api_key"

    @property
    def supported_modalities(self) -> list[str]:
        return ["text", "image", "audio", "video"]

    def pricing(self, model: str) -> PricingTier:
        if model not in _PRICING:
            raise KeyError(f"Unknown Gemma model: {model}")
        return _PRICING[model]
