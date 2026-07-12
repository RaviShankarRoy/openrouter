"""Semantic routing config loader (DRD §9.1, RT-002).

Reads `configs/routing.yaml` once at import time. The pool is filtered by
RequestHints capabilities (needs_tools, needs_vision, needs_streaming,
user_geo, data_residency_jurisdictions) before being handed to the strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import yaml

from app.application.routing.strategies import Candidate
from app.core.config import settings


@dataclass(frozen=True)
class PoolEntry:
    """A routable model with its capability surface."""

    model: str
    provider: str
    pricing_per_million: Decimal
    quality_score: float
    latency_p50_ms: float
    capabilities: frozenset[str]
    geos_allowed: frozenset[str]
    residency: frozenset[str]

    def to_candidate(self) -> Candidate:
        return Candidate(
            model=self.model,
            provider=self.provider,
            pricing_per_million=self.pricing_per_million,
            quality_score=self.quality_score,
            latency_p50_ms=self.latency_p50_ms,
        )


@dataclass(frozen=True)
class RoutingConfig:
    default_strategy: str
    fallback_max: int
    pool: tuple[PoolEntry, ...]
    quality_floor: float
    latency_max_ms: float

    def filter(
        self,
        *,
        needs_tools: bool = False,
        needs_vision: bool = False,
        needs_streaming: bool = False,
        user_geo: str = "",
        data_residency: tuple[str, ...] = (),
    ) -> list[Candidate]:
        """Apply RequestHints to the pool and return Candidates the strategy can rank."""
        required: set[str] = set()
        if needs_tools:
            required.add("tools")
        if needs_vision:
            required.add("vision")
        if needs_streaming:
            required.add("streaming")

        survivors: list[PoolEntry] = []
        for entry in self.pool:
            if not required.issubset(entry.capabilities):
                continue
            if user_geo and "*" not in entry.geos_allowed and user_geo not in entry.geos_allowed:
                continue
            if data_residency and not set(data_residency).intersection(entry.residency):
                continue
            if entry.quality_score < self.quality_floor:
                continue
            if entry.latency_p50_ms > self.latency_max_ms:
                continue
            survivors.append(entry)
        return [e.to_candidate() for e in survivors]


def _parse(raw: dict) -> RoutingConfig:
    pool = tuple(
        PoolEntry(
            model=item["model"],
            provider=item["provider"],
            pricing_per_million=Decimal(str(item["pricing_per_million"])),
            quality_score=float(item["quality_score"]),
            latency_p50_ms=float(item["latency_p50_ms"]),
            capabilities=frozenset(item.get("capabilities", [])),
            geos_allowed=frozenset(item.get("geos_allowed", ["*"])),
            residency=frozenset(item.get("residency", ["global"])),
        )
        for item in raw.get("pool", [])
    )
    floors = raw.get("strategy_floors", {})
    return RoutingConfig(
        default_strategy=raw.get("default_strategy", "cost"),
        fallback_max=int(raw.get("fallback_max", 2)),
        pool=pool,
        quality_floor=float(floors.get("quality", 0.0)),
        latency_max_ms=float(floors.get("latency_max_ms", 1e9)),
    )


@lru_cache(maxsize=1)
def get_routing_config() -> RoutingConfig:
    """Singleton load. Cleared by `reload_routing_config()` for SIGHUP reload."""
    path = Path(settings.routing_config_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return _parse(raw)


def reload_routing_config() -> RoutingConfig:
    """Validate-then-swap reload. If the new YAML is broken, keep serving the old one.

    Called by the SIGHUP handler registered in app/main.py — lets operators add
    models to `openrouter/auto` without restarting the backend pods.
    """
    # Try to load + parse first. If anything throws, the cache stays warm and
    # the existing config keeps serving requests.
    path = Path(settings.routing_config_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    new_cfg = _parse(raw)  # raises if malformed — cache untouched
    get_routing_config.cache_clear()
    # Re-prime the cache so the next call returns the validated value.
    cached = get_routing_config()
    assert cached.pool == new_cfg.pool, "cache primed with stale config"
    return cached
