"""SSE chunk emitter shared by all provider mocks.

The Go gateway's SSE proxy (GW-002) is one of the trickier paths to test; this
emitter generates realistic chunk boundaries and per-chunk delays so flow
control bugs surface in CI.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from src.scenarios import engine


async def stream_chunks(
    provider: str,
    route: str,
    chunks: list[dict[str, Any]],
) -> AsyncIterator[str]:
    """Yield each chunk as an SSE `data: {...}\\n\\n` event with delays.

    Terminates with the OpenAI/Anthropic convention `data: [DONE]\\n\\n`.
    """
    delay_ms = engine.stream_chunk_delay_ms(provider, route)
    for chunk in chunks:
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)
        yield f"data: {json.dumps(chunk)}\n\n"
    yield "data: [DONE]\n\n"
