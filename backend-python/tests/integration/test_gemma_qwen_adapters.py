"""Integration: Gemma + Qwen adapters against mocked HTTP via respx.

These adapters subclass OpenAIAdapter — they only override the base URL,
API key setting, name, and pricing. The tests verify:

  1. Requests hit the correct upstream base URL (Together / Fireworks).
  2. Responses are translated into UnifiedResponse correctly.
  3. Pricing math via the adapter's _PRICING dict is right.

This guards the most common failure mode of OpenAI-compatible adapters:
silently calling the wrong host because the subclass forgot to override
`_base_url`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import respx
from httpx import Response

from app.repository.providers.base import UnifiedRequest
from app.repository.providers.gemma_adapter import GemmaAdapter
from app.repository.providers.qwen_adapter import QwenAdapter


def _openai_shape(model: str, content: str, prompt_tokens: int = 5, completion_tokens: int = 2) -> dict:
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": 1700000000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


@pytest.mark.asyncio
@respx.mock(assert_all_called=True)
async def test_gemma_hits_fireworks(respx_mock: respx.Router) -> None:
    """GemmaAdapter must POST to Fireworks. The route's `called` flag plus
    respx's default "raise on unmatched request" together prove the right
    host is hit — any accidental call to openai.com would fail the test."""
    route = respx_mock.post("https://api.fireworks.ai/inference/v1/chat/completions").mock(
        return_value=Response(200, json=_openai_shape("google/gemma-4-31b", "ack"))
    )
    adapter = GemmaAdapter()
    resp = await adapter.complete(
        UnifiedRequest(
            model="google/gemma-4-31b",
            messages=[{"role": "user", "content": "hi"}],
        )
    )
    assert resp.content == "ack"
    assert resp.finish_reason == "stop"
    assert resp.usage.input == 5
    assert resp.usage.output == 2
    assert route.called, "GemmaAdapter did not hit Fireworks"


@pytest.mark.asyncio
@respx.mock(assert_all_called=True)
async def test_qwen_hits_together(respx_mock: respx.Router) -> None:
    """QwenAdapter must POST to Together."""
    route = respx_mock.post("https://api.together.xyz/v1/chat/completions").mock(
        return_value=Response(200, json=_openai_shape("qwen/qwen3.6-27b", "haiku here"))
    )
    adapter = QwenAdapter()
    resp = await adapter.complete(
        UnifiedRequest(
            model="qwen/qwen3.6-27b",
            messages=[{"role": "user", "content": "haiku?"}],
        )
    )
    assert resp.content == "haiku here"
    assert route.called, "QwenAdapter did not hit Together"


@pytest.mark.asyncio
async def test_gemma_pricing_math() -> None:
    """Pricing dict drives cost calculation — verify a known model produces the right cost."""
    from app.service.domain.value_objects import ModelPricing, TokenCounts

    tier = GemmaAdapter().pricing("google/gemma-4-31b")
    pricing = ModelPricing(
        input_per_million=tier.input_per_million,
        output_per_million=tier.output_per_million,
    )
    # 1M input @ $0.30 + 1M output @ $0.50 = $0.80
    cost = pricing.cost(TokenCounts(input=1_000_000, output=1_000_000))
    assert cost.amount == Decimal("0.80")


@pytest.mark.asyncio
async def test_qwen_pricing_math() -> None:
    from app.service.domain.value_objects import ModelPricing, TokenCounts

    tier = QwenAdapter().pricing("qwen/qwen3.6-27b")
    pricing = ModelPricing(
        input_per_million=tier.input_per_million,
        output_per_million=tier.output_per_million,
    )
    # 1M input @ $0.20 + 1M output @ $0.60 = $0.80
    cost = pricing.cost(TokenCounts(input=1_000_000, output=1_000_000))
    assert cost.amount == Decimal("0.80")


@pytest.mark.asyncio
@respx.mock(assert_all_called=True)
async def test_provider_name_is_independent_of_base_url(respx_mock: respx.Router) -> None:
    """Regression guard: adapter.name must reflect the gateway-side provider id
    (`gemma`, `qwen`) — not the host it physically calls (Fireworks, Together).

    This matters because usage_records.provider is keyed on .name; getting
    it wrong silently mis-attributes billing rows.
    """
    respx_mock.post("https://api.fireworks.ai/inference/v1/chat/completions").mock(
        return_value=Response(200, json=_openai_shape("google/gemma-4-e4b", ""))
    )
    respx_mock.post("https://api.together.xyz/v1/chat/completions").mock(
        return_value=Response(200, json=_openai_shape("qwen/qwen3.6-27b", ""))
    )
    assert GemmaAdapter().name == "gemma"
    assert QwenAdapter().name == "qwen"
    # Smoke each through their host so respx confirms the URL.
    await GemmaAdapter().complete(
        UnifiedRequest(model="google/gemma-4-e4b", messages=[{"role": "user", "content": "x"}])
    )
    await QwenAdapter().complete(
        UnifiedRequest(model="qwen/qwen3.6-27b", messages=[{"role": "user", "content": "x"}])
    )
