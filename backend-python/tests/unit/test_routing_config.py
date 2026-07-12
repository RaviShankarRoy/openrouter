"""Tests for the semantic routing config loader and filter logic.

Pool fixtures are inline so tests don't depend on the shipped routing.yaml
contents — that file is operator-tunable.
"""
from __future__ import annotations

import textwrap
from decimal import Decimal
from pathlib import Path

import pytest

from app.application.routing.config import RoutingConfig, _parse, get_routing_config
from app.application.routing.strategies import StrategyRegistry


@pytest.fixture
def tiny_config() -> RoutingConfig:
    raw = {
        "default_strategy": "cost",
        "fallback_max": 1,
        "strategy_floors": {"quality": 0.70, "latency_max_ms": 1000},
        "pool": [
            {
                "model": "cheap",
                "provider": "p1",
                "pricing_per_million": 0.10,
                "quality_score": 0.75,
                "latency_p50_ms": 200,
                "capabilities": ["text", "streaming"],
                "geos_allowed": ["*"],
                "residency": ["us", "global"],
            },
            {
                "model": "vision",
                "provider": "p2",
                "pricing_per_million": 0.50,
                "quality_score": 0.90,
                "latency_p50_ms": 800,
                "capabilities": ["text", "vision", "tools", "streaming"],
                "geos_allowed": ["*"],
                "residency": ["us", "eu", "global"],
            },
            {
                "model": "low-quality",
                "provider": "p3",
                "pricing_per_million": 0.01,
                "quality_score": 0.40,  # below floor
                "latency_p50_ms": 50,
                "capabilities": ["text"],
                "geos_allowed": ["*"],
                "residency": ["self_hosted"],
            },
            {
                "model": "slow",
                "provider": "p4",
                "pricing_per_million": 0.05,
                "quality_score": 0.85,
                "latency_p50_ms": 5000,  # above ceiling
                "capabilities": ["text"],
                "geos_allowed": ["*"],
                "residency": ["global"],
            },
        ],
    }
    return _parse(raw)


def test_filter_no_hints_drops_floor_violators(tiny_config: RoutingConfig) -> None:
    survivors = tiny_config.filter()
    models = {c.model for c in survivors}
    assert "cheap" in models
    assert "vision" in models
    assert "low-quality" not in models, "quality below floor must drop"
    assert "slow" not in models, "latency above ceiling must drop"


def test_filter_needs_vision(tiny_config: RoutingConfig) -> None:
    survivors = tiny_config.filter(needs_vision=True)
    assert {c.model for c in survivors} == {"vision"}


def test_filter_residency_eu(tiny_config: RoutingConfig) -> None:
    survivors = tiny_config.filter(data_residency=("eu",))
    assert {c.model for c in survivors} == {"vision"}


def test_filter_no_candidates_returns_empty(tiny_config: RoutingConfig) -> None:
    # A capability nothing in the pool has.
    assert tiny_config.filter(needs_vision=True, data_residency=("self_hosted",)) == []


def test_cost_strategy_picks_cheapest_after_filter(tiny_config: RoutingConfig) -> None:
    candidates = tiny_config.filter()
    decision = StrategyRegistry.default().get("cost").choose(candidates)
    assert decision.primary.model == "cheap"
    assert decision.primary.pricing_per_million == Decimal("0.10")


def test_get_routing_config_loads_real_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Loader points at routing_config_path from settings; ensure it can read a real file."""
    routing = tmp_path / "routing.yaml"
    routing.write_text(
        textwrap.dedent("""
        default_strategy: latency
        fallback_max: 0
        strategy_floors:
          quality: 0.0
          latency_max_ms: 999999
        pool:
          - model: only
            provider: x
            pricing_per_million: 1.0
            quality_score: 0.5
            latency_p50_ms: 100
            capabilities: [text]
            geos_allowed: ["*"]
            residency: [global]
        """).strip()
    )
    from app.core.config import settings

    monkeypatch.setattr(settings, "routing_config_path", str(routing))
    get_routing_config.cache_clear()
    cfg = get_routing_config()
    assert cfg.default_strategy == "latency"
    assert len(cfg.pool) == 1
    assert cfg.pool[0].model == "only"
    get_routing_config.cache_clear()  # don't leak fixture into other tests
