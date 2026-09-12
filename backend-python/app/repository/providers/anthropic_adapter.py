"""Anthropic provider adapter — Messages API translation."""
from __future__ import annotations

import time
from decimal import Decimal
from typing import AsyncIterator

from anthropic import AsyncAnthropic

from app.shared.config import settings
from app.repository.providers.base import (
    HealthStatus,
    PricingTier,
    ProviderAdapter,
    TokenCount,
    UnifiedChunk,
    UnifiedRequest,
    UnifiedResponse,
)

_PRICING: dict[str, PricingTier] = {
    "claude-sonnet-4-20250514": PricingTier(
        input_per_million=Decimal("3.00"),
        output_per_million=Decimal("15.00"),
        cached_input_per_million=Decimal("0.30"),
    ),
    "claude-opus-4-20250514": PricingTier(
        input_per_million=Decimal("15.00"),
        output_per_million=Decimal("75.00"),
    ),
    "claude-haiku-4-20250514": PricingTier(
        input_per_million=Decimal("0.80"),
        output_per_million=Decimal("4.00"),
    ),
}


class AnthropicAdapter(ProviderAdapter):
    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def supported_modalities(self) -> list[str]:
        return ["text", "image"]

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())

    async def complete(self, req: UnifiedRequest) -> UnifiedResponse:
        system, messages = self._split_system(req.messages)
        kwargs: dict = {
            "model": _strip_prefix(req.model),
            "messages": messages,
            "max_tokens": req.max_tokens or 4096,
        }
        if system:
            kwargs["system"] = system
        if req.temperature is not None:
            kwargs["temperature"] = req.temperature
        if req.tools:
            kwargs["tools"] = req.tools

        resp = await self._client.messages.create(**kwargs)
        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        tool_calls = [
            {"id": block.id, "type": "function", "function": {"name": block.name, "arguments": block.input}}
            for block in resp.content
            if getattr(block, "type", None) == "tool_use"
        ]
        return UnifiedResponse(
            id=resp.id,
            model=resp.model,
            content=text,
            finish_reason=_map_stop_reason(resp.stop_reason or "end_turn"),
            tool_calls=tool_calls or None,
            usage=TokenCount(
                input=resp.usage.input_tokens,
                output=resp.usage.output_tokens,
                cached_input=getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
            ),
            raw=resp.model_dump(),
        )

    async def stream(self, req: UnifiedRequest) -> AsyncIterator[UnifiedChunk]:
        system, messages = self._split_system(req.messages)
        kwargs: dict = {
            "model": _strip_prefix(req.model),
            "messages": messages,
            "max_tokens": req.max_tokens or 4096,
        }
        if system:
            kwargs["system"] = system
        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and hasattr(event.delta, "text"):
                    yield UnifiedChunk(
                        delta_text=event.delta.text,
                        delta_tool_calls=None,
                        finish_reason=None,
                    )
                elif event.type == "message_stop":
                    yield UnifiedChunk(delta_text="", delta_tool_calls=None, finish_reason="stop")

    async def count_tokens(self, model: str, messages: list[dict]) -> int:
        # Anthropic's count_tokens endpoint exists but is rate-limited; for hot-path
        # estimates use char/4 heuristic or cache results.
        chars = sum(len(str(m.get("content", ""))) for m in messages)
        return chars // 4

    async def health_check(self) -> HealthStatus:
        start = time.perf_counter()
        try:
            # Lightest call: a 1-token completion.
            await self._client.messages.create(
                model="claude-haiku-4-20250514",
                messages=[{"role": "user", "content": "ok"}],
                max_tokens=1,
            )
            return HealthStatus(healthy=True, latency_ms=int((time.perf_counter() - start) * 1000))
        except Exception as exc:
            return HealthStatus(
                healthy=False,
                latency_ms=int((time.perf_counter() - start) * 1000),
                last_error=str(exc),
            )

    def pricing(self, model: str) -> PricingTier:
        clean = _strip_prefix(model)
        if clean not in _PRICING:
            raise KeyError(f"Unknown model: {model}")
        return _PRICING[clean]

    @staticmethod
    def _split_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
        system_parts: list[str] = []
        rest: list[dict] = []
        for m in messages:
            if m.get("role") == "system":
                system_parts.append(str(m.get("content", "")))
            else:
                rest.append(m)
        return ("\n\n".join(system_parts) if system_parts else None, rest)


def _strip_prefix(model: str) -> str:
    return model.split("/", 1)[1] if "/" in model else model


def _map_stop_reason(s: str) -> str:
    return {
        "end_turn": "stop",
        "max_tokens": "length",
        "tool_use": "tool_calls",
        "stop_sequence": "stop",
    }.get(s, "stop")
