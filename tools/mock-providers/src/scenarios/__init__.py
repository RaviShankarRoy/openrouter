"""Scenario engine — runtime-tunable behavior shared by every provider mock.

Each provider route asks the engine "what should I do?" before responding. The
control plane (src/control/admin.py) mutates engine state so tests can flip a
switch without restarting.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from src.config import settings


@dataclass
class ScenarioState:
    """Per-(provider, route) override. Falls back to settings defaults."""

    latency_ms: float | None = None
    error_rate: float | None = None
    rate_limit_rate: float | None = None
    stream_chunk_delay_ms: float | None = None
    # One-shot forced status — useful for deterministic test scripts.
    force_status: int | None = None


@dataclass
class _Stats:
    requests: int = 0
    errors_injected: int = 0
    rate_limits_injected: int = 0
    latency_total_ms: float = 0.0


class ScenarioEngine:
    """Thread-safe registry of overrides + counters."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._overrides: dict[tuple[str, str], ScenarioState] = {}
        self._stats: _Stats = _Stats()

    # ----- mutators (called by control plane) -------------------------------

    def set(self, provider: str, route: str, **kwargs: float | int | None) -> ScenarioState:
        with self._lock:
            state = self._overrides.setdefault((provider, route), ScenarioState())
            for k, v in kwargs.items():
                if hasattr(state, k):
                    setattr(state, k, v)
            return state

    def reset(self) -> None:
        with self._lock:
            self._overrides.clear()
            self._stats = _Stats()

    # ----- accessors (called by routes) -------------------------------------

    def get(self, provider: str, route: str) -> ScenarioState:
        with self._lock:
            return self._overrides.get((provider, route), ScenarioState())

    def latency_ms(self, provider: str, route: str) -> float:
        s = self.get(provider, route)
        return s.latency_ms if s.latency_ms is not None else settings.default_latency_ms

    def error_rate(self, provider: str, route: str) -> float:
        s = self.get(provider, route)
        return s.error_rate if s.error_rate is not None else settings.default_error_rate

    def rate_limit_rate(self, provider: str, route: str) -> float:
        s = self.get(provider, route)
        return (
            s.rate_limit_rate
            if s.rate_limit_rate is not None
            else settings.default_rate_limit_rate
        )

    def stream_chunk_delay_ms(self, provider: str, route: str) -> float:
        s = self.get(provider, route)
        return (
            s.stream_chunk_delay_ms
            if s.stream_chunk_delay_ms is not None
            else settings.stream_chunk_delay_ms
        )

    def take_force_status(self, provider: str, route: str) -> int | None:
        with self._lock:
            state = self._overrides.get((provider, route))
            if state is None:
                return None
            forced = state.force_status
            state.force_status = None
            return forced

    # ----- stats -----------------------------------------------------------

    def record(self, *, latency_ms: float, error: bool = False, rate_limit: bool = False) -> None:
        with self._lock:
            self._stats.requests += 1
            self._stats.latency_total_ms += latency_ms
            if error:
                self._stats.errors_injected += 1
            if rate_limit:
                self._stats.rate_limits_injected += 1

    def stats(self) -> dict[str, object]:
        with self._lock:
            return {
                "requests": self._stats.requests,
                "errors_injected": self._stats.errors_injected,
                "rate_limits_injected": self._stats.rate_limits_injected,
                "avg_latency_ms": (
                    self._stats.latency_total_ms / self._stats.requests
                    if self._stats.requests
                    else 0.0
                ),
                "overrides": {
                    f"{p}:{r}": vars(state) for (p, r), state in self._overrides.items()
                },
            }


# Module-level singleton — every route just imports `engine`.
engine = ScenarioEngine()
