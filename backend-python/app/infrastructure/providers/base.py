"""Provider adapter base class — DRD §7.2 verbatim.

Pattern: Adapter + Template Method. Subclasses implement provider-specific
translations; the base class provides shared utilities (timeouts, retries,
metric emission).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import AsyncIterator


@dataclass(frozen=True)
class UnifiedRequest:
    """OpenAI-compatible request shape used internally."""

    model: str
    messages: list[dict]
    stream: bool = False
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    tools: list[dict] | None = None
    response_format: dict | None = None
    reasoning_effort: str | None = None
    extras: dict | None = None  # provider passthrough (DRD PI-003)


@dataclass(frozen=True)
class UnifiedResponse:
    """OpenAI-compatible response shape returned to the gateway."""

    id: str
    model: str
    content: str
    finish_reason: str  # stop | length | tool_calls | content_filter | error
    tool_calls: list[dict] | None
    usage: TokenCount
    raw: dict  # original provider payload, for diagnostics


@dataclass(frozen=True)
class UnifiedChunk:
    """A single SSE chunk in OpenAI streaming format."""

    delta_text: str
    delta_tool_calls: list[dict] | None
    finish_reason: str | None


@dataclass(frozen=True)
class TokenCount:
    input: int
    output: int
    cached_input: int = 0
    reasoning: int = 0


@dataclass(frozen=True)
class PricingTier:
    input_per_million: Decimal
    output_per_million: Decimal
    cached_input_per_million: Decimal | None = None
    reasoning_per_million: Decimal | None = None


@dataclass(frozen=True)
class HealthStatus:
    healthy: bool
    latency_ms: int
    last_error: str | None = None


class ProviderAdapter(ABC):
    """Contract every provider implements."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def supported_modalities(self) -> list[str]: ...

    @abstractmethod
    async def complete(self, req: UnifiedRequest) -> UnifiedResponse: ...

    @abstractmethod
    async def stream(self, req: UnifiedRequest) -> AsyncIterator[UnifiedChunk]: ...

    @abstractmethod
    async def count_tokens(self, model: str, messages: list[dict]) -> int: ...

    @abstractmethod
    async def health_check(self) -> HealthStatus: ...

    @abstractmethod
    def pricing(self, model: str) -> PricingTier: ...
