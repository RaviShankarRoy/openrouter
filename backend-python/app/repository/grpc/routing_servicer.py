"""RoutingService gRPC servicer — resolves "openrouter/auto" requests (DRD RT-002, §9.1).

Pipeline:
  1. Load candidate pool from configs/routing.yaml (cached, see routing.config).
  2. Filter the pool by RequestHints (tools/vision/streaming, geo, residency).
  3. Pick a strategy: per-key override (future) → request hint → config default.
  4. Run StrategyRegistry to rank candidates → return primary + fallback chain.

The pool, capability flags, quality scores, and latency baselines all live
in routing.yaml so we never need to redeploy to add a new model to auto.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.service.routing.config import get_routing_config
from app.service.routing.strategies import StrategyRegistry
from app.shared.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from app.repository.grpc.gen.routing.v1 import routing_pb2, routing_pb2_grpc  # noqa: F401

try:
    from app.repository.grpc.gen.routing.v1 import routing_pb2, routing_pb2_grpc  # type: ignore[import-not-found]

    _BASE = routing_pb2_grpc.RoutingServiceServicer
except ImportError:
    routing_pb2 = None  # type: ignore[assignment]
    _BASE = object  # type: ignore[assignment,misc]

_log = get_logger(__name__)

# Sentinel fallback if every candidate is filtered out (DRD RT-002).
_SENTINEL_MODEL = "gpt-4o-mini"
_SENTINEL_PROVIDER = "openai"


class RoutingServicer(_BASE):  # type: ignore[misc,valid-type]
    def __init__(self, strategies: StrategyRegistry | None = None) -> None:
        self._strategies = strategies or StrategyRegistry.default()

    async def ResolveModel(self, request: Any, context: Any) -> Any:  # noqa: N802
        if routing_pb2 is None:  # pragma: no cover
            raise RuntimeError("routing_pb2 not generated — run `make proto`")

        cfg = get_routing_config()
        hints = getattr(request, "hints", None)
        candidates = cfg.filter(
            needs_tools=bool(getattr(hints, "needs_tools", False)),
            needs_vision=bool(getattr(hints, "needs_vision", False)),
            needs_streaming=bool(getattr(hints, "needs_streaming", False)),
            user_geo=str(getattr(hints, "user_geo", "") or ""),
            data_residency=tuple(getattr(hints, "data_residency_jurisdictions", []) or ()),
        )

        if not candidates:
            _log.warning(
                "routing_no_candidates",
                org_id=getattr(request, "org_id", ""),
                requested=getattr(request, "requested_model", ""),
            )
            return routing_pb2.ResolveModelResponse(
                primary_model=_SENTINEL_MODEL,
                primary_provider=_SENTINEL_PROVIDER,
                fallback_chain=[],
                strategy_used="sentinel",
            )

        strategy = self._strategies.get(cfg.default_strategy)
        decision = strategy.choose(candidates)
        fallbacks = decision.fallback[: cfg.fallback_max]

        _log.info(
            "routing_resolved",
            org_id=getattr(request, "org_id", ""),
            primary=decision.primary.model,
            provider=decision.primary.provider,
            strategy=decision.strategy,
            n_fallback=len(fallbacks),
        )

        return routing_pb2.ResolveModelResponse(
            primary_model=decision.primary.model,
            primary_provider=decision.primary.provider,
            fallback_chain=[
                routing_pb2.FallbackTarget(model=c.model, provider=c.provider)
                for c in fallbacks
            ],
            strategy_used=decision.strategy,
        )

    async def ProviderScores(self, request: Any, context: Any) -> Any:  # noqa: N802
        if routing_pb2 is None:  # pragma: no cover
            raise RuntimeError("routing_pb2 not generated — run `make proto`")

        cfg = get_routing_config()
        wanted = set(getattr(request, "models", []) or [])
        # Latency p50 → 0..1 score (lower latency = higher score). Anchored at 2000ms.
        scores = []
        for entry in cfg.pool:
            if wanted and entry.model not in wanted:
                continue
            score = max(0.0, min(1.0, 1.0 - (entry.latency_p50_ms / 2000.0)))
            scores.append(
                routing_pb2.ProviderScore(
                    model=entry.model,
                    provider=entry.provider,
                    score=score,
                    last_updated_unix=0,
                )
            )
        return routing_pb2.ProviderScoresResponse(scores=scores)
