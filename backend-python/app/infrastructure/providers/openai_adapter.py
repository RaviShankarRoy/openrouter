"""OpenAI provider adapter — reference implementation."""
from __future__ import annotations

import time
from decimal import Decimal
from typing import AsyncIterator

import tiktoken
from openai import AsyncOpenAI

from app.core.config import settings
from app.infrastructure.providers.base import (
    HealthStatus,
    PricingTier,
    ProviderAdapter,
    TokenCount,
    UnifiedChunk,
    UnifiedRequest,
    UnifiedResponse,
)

# Phase-1 catalog. Production loads from the models_catalog table.
_PRICING: dict[str, PricingTier] = {
    "gpt-4o": PricingTier(
        input_per_million=Decimal("2.50"),
        output_per_million=Decimal("10.00"),
        cached_input_per_million=Decimal("1.25"),
    ),
    "gpt-4o-mini": PricingTier(
        input_per_million=Decimal("0.15"),
        output_per_million=Decimal("0.60"),
    ),
}


class OpenAIAdapter(ProviderAdapter):
    # Subclasses for OpenAI-compatible providers (Gemma 4 via Fireworks,
    # Qwen via Together, etc.) override these three.
    _provider_name: str = "openai"
    _base_url: str | None = None  # None → AsyncOpenAI default (api.openai.com)
    _api_key_setting: str = "openai_api_key"

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def supported_modalities(self) -> list[str]:
        return ["text", "image", "audio", "embeddings"]

    def __init__(self) -> None:
        api_key = getattr(settings, self._api_key_setting).get_secret_value()
        kwargs: dict = {"api_key": api_key or "unset"}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        self._client = AsyncOpenAI(**kwargs)

    async def complete(self, req: UnifiedRequest) -> UnifiedResponse:
        kwargs: dict = {
            "model": req.model,
            "messages": req.messages,
            "stream": False,
        }
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature
        if req.tools:
            kwargs["tools"] = req.tools
        if req.response_format:
            kwargs["response_format"] = req.response_format
        if req.reasoning_effort:
            kwargs["reasoning_effort"] = req.reasoning_effort

        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return UnifiedResponse(
            id=resp.id,
            model=resp.model,
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
            tool_calls=[tc.model_dump() for tc in (choice.message.tool_calls or [])] or None,
            usage=TokenCount(
                input=resp.usage.prompt_tokens,
                output=resp.usage.completion_tokens,
                cached_input=getattr(resp.usage, "prompt_tokens_details", {})
                and getattr(resp.usage.prompt_tokens_details, "cached_tokens", 0)
                or 0,
            ),
            raw=resp.model_dump(),
        )

    async def stream(self, req: UnifiedRequest) -> AsyncIterator[UnifiedChunk]:
        kwargs: dict = {
            "model": req.model,
            "messages": req.messages,
            "stream": True,
        }
        if req.max_tokens is not None:
            kwargs["max_tokens"] = req.max_tokens
        async for chunk in await self._client.chat.completions.create(**kwargs):
            choice = chunk.choices[0]
            yield UnifiedChunk(
                delta_text=choice.delta.content or "",
                delta_tool_calls=[tc.model_dump() for tc in (choice.delta.tool_calls or [])] or None,
                finish_reason=choice.finish_reason,
            )

    async def count_tokens(self, model: str, messages: list[dict]) -> int:
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return sum(len(enc.encode(str(m.get("content", "")))) for m in messages)

    async def health_check(self) -> HealthStatus:
        start = time.perf_counter()
        try:
            await self._client.models.list()
            return HealthStatus(healthy=True, latency_ms=int((time.perf_counter() - start) * 1000))
        except Exception as exc:
            return HealthStatus(
                healthy=False,
                latency_ms=int((time.perf_counter() - start) * 1000),
                last_error=str(exc),
            )

    def pricing(self, model: str) -> PricingTier:
        if model not in _PRICING:
            raise KeyError(f"Unknown model: {model}")
        return _PRICING[model]
