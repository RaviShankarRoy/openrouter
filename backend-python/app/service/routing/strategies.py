"""Routing strategies — Strategy pattern for "openrouter/auto" resolution.

DRD §9.1: cost / latency / quality / geo / semantic.
The Go gateway handles explicit-model routing; Python only runs when the
client requests `openrouter/auto` or semantic routing is enabled per-key.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Candidate:
    model: str
    provider: str
    pricing_per_million: Decimal
    quality_score: float  # 0..1 from Auto Exacto (DRD §9.2)
    latency_p50_ms: float


@dataclass(frozen=True)
class RoutingDecision:
    primary: Candidate
    fallback: list[Candidate]
    strategy: str


class RoutingStrategy(ABC):
    name: str

    @abstractmethod
    def choose(self, candidates: list[Candidate]) -> RoutingDecision: ...


class CostStrategy(RoutingStrategy):
    name = "cost"

    def choose(self, candidates: list[Candidate]) -> RoutingDecision:
        ranked = sorted(candidates, key=lambda c: c.pricing_per_million)
        return RoutingDecision(primary=ranked[0], fallback=ranked[1:], strategy=self.name)


class LatencyStrategy(RoutingStrategy):
    name = "latency"

    def choose(self, candidates: list[Candidate]) -> RoutingDecision:
        ranked = sorted(candidates, key=lambda c: c.latency_p50_ms)
        return RoutingDecision(primary=ranked[0], fallback=ranked[1:], strategy=self.name)


class QualityStrategy(RoutingStrategy):
    name = "quality"

    def choose(self, candidates: list[Candidate]) -> RoutingDecision:
        ranked = sorted(candidates, key=lambda c: c.quality_score, reverse=True)
        return RoutingDecision(primary=ranked[0], fallback=ranked[1:], strategy=self.name)


class StrategyRegistry:
    """Registry of named strategies — extensible by future plugins."""

    def __init__(self, strategies: list[RoutingStrategy]) -> None:
        self._by_name = {s.name: s for s in strategies}

    def get(self, name: str) -> RoutingStrategy:
        if name not in self._by_name:
            raise KeyError(f"Unknown routing strategy: {name}")
        return self._by_name[name]

    @classmethod
    def default(cls) -> "StrategyRegistry":
        return cls([CostStrategy(), LatencyStrategy(), QualityStrategy()])
