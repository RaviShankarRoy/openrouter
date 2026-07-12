"""Env-driven config. Defaults are safe for local dev and CI.

Pydantic is intentionally NOT used here — config must be readable from a single
process-wide instance with zero deps so tests can mutate it cleanly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    return float(raw) if raw is not None else default


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    return int(raw) if raw is not None else default


@dataclass
class ModelEntry:
    """Single entry exposed via the model registry."""

    id: str
    provider: str
    context_window: int
    supports_tools: bool = True
    supports_streaming: bool = True


@dataclass
class Settings:
    port: int = field(default_factory=lambda: _env_int("MOCK_PORT", 9100))
    log_level: str = field(default_factory=lambda: os.environ.get("MOCK_LOG_LEVEL", "info"))

    # Defaults that scenarios can override at runtime via /control/scenario.
    default_latency_ms: float = field(
        default_factory=lambda: _env_float("MOCK_DEFAULT_LATENCY_MS", 5.0)
    )
    default_error_rate: float = field(
        default_factory=lambda: _env_float("MOCK_DEFAULT_ERROR_RATE", 0.0)
    )
    default_rate_limit_rate: float = field(
        default_factory=lambda: _env_float("MOCK_DEFAULT_RATE_LIMIT_RATE", 0.0)
    )
    stream_chunk_delay_ms: float = field(
        default_factory=lambda: _env_float("MOCK_STREAM_CHUNK_DELAY_MS", 20.0)
    )

    # Tiny in-process registry — keeps tests independent of backend-python.
    # Open-weight models served via OpenAI-compatible aggregators (Together,
    # Fireworks, Ollama) use the openai mock router; the `provider` field here
    # is the *logical* gateway provider name so scenario injection keys match.
    models: list[ModelEntry] = field(
        default_factory=lambda: [
            ModelEntry("gpt-4o-mini", "openai", 128_000),
            ModelEntry("gpt-4o", "openai", 128_000),
            ModelEntry("text-embedding-3-small", "openai", 8_191, supports_tools=False),
            ModelEntry("dall-e-3", "openai", 0, supports_tools=False, supports_streaming=False),
            ModelEntry("claude-3-5-sonnet-20241022", "anthropic", 200_000),
            ModelEntry("claude-3-5-haiku-20241022", "anthropic", 200_000),
            ModelEntry("gemini-1.5-pro", "google", 2_000_000),
            ModelEntry("gemini-1.5-flash", "google", 1_000_000),
            # Open-weight catalog (Apache 2.0) — added in the Gemma 4 + Qwen 3.6
            # integration. Same `provider` names the Go gateway uses.
            ModelEntry("google/gemma-4-31b", "fireworks", 256_000),
            ModelEntry("google/gemma-4-26b-moe", "fireworks", 256_000),
            ModelEntry("google/gemma-4-e4b", "ollama", 128_000),
            ModelEntry("google/gemma-4-e2b", "ollama", 128_000),
            ModelEntry("qwen/qwen3.6-27b", "together", 128_000),
            ModelEntry("qwen/qwen3.6-35b-a3b", "together", 128_000),
            ModelEntry("qwen/qwen3.5-35b-a3b", "together", 128_000),
            ModelEntry("qwen/qwen3.5-122b-a10b", "fireworks", 128_000),
        ]
    )


settings = Settings()
