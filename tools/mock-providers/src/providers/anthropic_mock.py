"""Anthropic-compatible mock — `/v1/messages` with content blocks.

Shapes follow the Anthropic Messages API so the gateway's anthropic adapter can
hit this server unchanged.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from src.scenarios import engine
from src.scenarios.errors import maybe_inject_error
from src.scenarios.latency import sleep_with_jitter
from src.scenarios.streaming import stream_chunks

router = APIRouter()
PROVIDER = "anthropic"


def _id() -> str:
    return f"msg_{uuid.uuid4().hex[:24]}"


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _build_response(req: dict[str, Any]) -> dict[str, Any]:
    model = req.get("model", "claude-3-5-sonnet-20241022")
    messages = req.get("messages", [])
    user_text = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content")
            if isinstance(content, str):
                user_text = content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        user_text = block.get("text", "")
                        break
            break

    tools = req.get("tools")

    if tools:
        # PI-004 — Anthropic emits tool_use content blocks instead of tool_calls.
        tool = tools[0]
        content_blocks: list[dict[str, Any]] = [
            {
                "type": "tool_use",
                "id": f"toolu_{uuid.uuid4().hex[:16]}",
                "name": tool.get("name", "do_something"),
                "input": {"query": "mock"},
            }
        ]
        stop_reason = "tool_use"
    else:
        content_blocks = [{"type": "text", "text": f"Mocked reply to: {user_text[:80]}"}]
        stop_reason = "end_turn"

    input_tokens = sum(
        _approx_tokens(str(m.get("content", ""))) for m in messages if isinstance(m, dict)
    )
    output_tokens = sum(_approx_tokens(str(b.get("text", b.get("name", "")))) for b in content_blocks)

    return {
        "id": _id(),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content_blocks,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


def _stream_events(req: dict[str, Any]) -> list[dict[str, Any]]:
    """Anthropic's SSE stream uses typed events — message_start, content_block_*, etc."""
    msg_id = _id()
    model = req.get("model", "claude-3-5-sonnet-20241022")
    text = "Mocked streaming reply."
    events: list[dict[str, Any]] = []
    events.append(
        {
            "type": "message_start",
            "message": {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": model,
                "stop_reason": None,
                "usage": {"input_tokens": 1, "output_tokens": 0},
            },
        }
    )
    events.append({"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})
    for word in text.split(" "):
        events.append(
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": word + " "},
            }
        )
    events.append({"type": "content_block_stop", "index": 0})
    events.append(
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": _approx_tokens(text)},
        }
    )
    events.append({"type": "message_stop"})
    return events


@router.post("/messages")
async def messages(request: Request) -> Any:
    route = "messages"
    body = await request.json()
    maybe_inject_error(PROVIDER, route)
    slept = await sleep_with_jitter(engine.latency_ms(PROVIDER, route))

    if body.get("stream"):
        events = _stream_events(body)
        engine.record(latency_ms=slept)
        return EventSourceResponse(stream_chunks(PROVIDER, route, events))

    engine.record(latency_ms=slept)
    return _build_response(body)


# Re-export for callers that prefer the lower-level helper.
__all__ = ["router", "time"]
