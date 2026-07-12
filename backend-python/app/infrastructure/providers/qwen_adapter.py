"""Qwen 3.x adapter — served via Together (OpenAI-compatible).

Apache 2.0 weights. Text + tool calling. Vision-capable Qwen variants
(Qwen 2.5-VL etc.) can be added later as a separate adapter or by
extending supported_modalities once VL Qwen 3 lands.
"""
from __future__ import annotations

from decimal import Decimal

from app.infrastructure.providers.base import PricingTier
from app.infrastructure.providers.openai_adapter import OpenAIAdapter

# Phase-1 catalog. Production loads from the model_pricing table.
_PRICING: dict[str, PricingTier] = {
    "qwen/qwen3.6-27b": PricingTier(
        input_per_million=Decimal("0.20"),
        output_per_million=Decimal("0.60"),
    ),
    "qwen/qwen3.6-35b-a3b": PricingTier(
        input_per_million=Decimal("0.27"),
        output_per_million=Decimal("0.85"),
    ),
    "qwen/qwen3.5-35b-a3b": PricingTier(
        input_per_million=Decimal("0.27"),
        output_per_million=Decimal("0.85"),
    ),
    "qwen/qwen3.5-122b-a10b": PricingTier(
        input_per_million=Decimal("0.60"),
        output_per_million=Decimal("1.80"),
    ),
}


class QwenAdapter(OpenAIAdapter):
    _provider_name = "qwen"
    _base_url = "https://api.together.xyz/v1"
    _api_key_setting = "together_api_key"

    @property
    def supported_modalities(self) -> list[str]:
        return ["text"]

    def pricing(self, model: str) -> PricingTier:
        if model not in _PRICING:
            raise KeyError(f"Unknown Qwen model: {model}")
        return _PRICING[model]
