"""Fallback-chain scenario helpers.

The gateway's fallback chain (providers.yaml `fallback: [...]`) is only
exercised when a primary provider returns 5xx or 429. These helpers wrap the
generic scenario engine to make "kill provider X, leave Y healthy" a one-liner
in tests.

Usage from a test (pytest or shell):

    # Make every Together call return 503 for the next 30 seconds, so the
    # gateway falls back to Fireworks for Qwen requests.
    POST /control/scenario  {"provider": "together", "route": "chat",
                             "force_status": 503}

    # Or use the helper from a Python test:
    from src.scenarios.fallback import break_provider, heal_provider
    break_provider("together", "chat", status=503)
    ...
    heal_provider("together", "chat")
"""

from __future__ import annotations

from src.scenarios import engine


def break_provider(provider: str, route: str = "chat", *, status: int = 503) -> None:
    """Force the next call to (provider, route) to return `status`.

    Default 503 mimics an upstream outage that should trigger the gateway's
    fallback chain. Use 429 to test rate-limit-driven fallback instead.
    """
    engine.set(provider, route, force_status=status)


def heal_provider(provider: str, route: str = "chat") -> None:
    """Clear any forced status — subsequent calls behave normally."""
    engine.set(provider, route, force_status=None)


def degrade_provider(
    provider: str, route: str = "chat", *, latency_ms: float = 2000.0
) -> None:
    """Add deterministic latency to (provider, route) so a latency-strategy
    test can verify routing shifts to a faster alternative."""
    engine.set(provider, route, latency_ms=latency_ms)


def stop_all() -> None:
    """Convenience: clear every override and reset stats counters."""
    engine.reset()
