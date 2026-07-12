"""OpenAI-compatible mock — chat, embeddings, images.

Shapes match `openai-python` v1 SDK so an unmodified adapter cannot tell the
difference. Tool calls (PI-004) and structured outputs (PI-005) are emitted
when the request asks for them.
"""

from __future__ import annotations

import base64
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

PROVIDER = "openai"

# 1x1 transparent PNG — used by /v1/images/generations responses.
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def _now() -> int:
    return int(time.time())


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:24]}"


def _approx_tokens(text: str) -> int:
    """Cheap token estimate — good enough for usage telemetry shape testing."""
    return max(1, len(text) // 4)


# ---------------- /v1/chat/completions ----------------------------------------


def _build_chat_response(req: dict[str, Any]) -> dict[str, Any]:
    model = req.get("model", "gpt-4o-mini")
    messages = req.get("messages", [])
    last_user = next((m for m in reversed(messages) if m.get("role") == "user"), {})
    user_text = last_user.get("content", "") if isinstance(last_user.get("content"), str) else ""

    tools = req.get("tools")
    response_format = req.get("response_format") or {}

    # PI-004 — emit a tool_calls reply when the request advertises tools.
    if tools:
        tool = tools[0]
        function_name = tool.get("function", {}).get("name", "do_something")
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": _id("call"),
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "arguments": '{"query":"mock"}',
                    },
                }
            ],
        }
        finish_reason = "tool_calls"
    elif response_format.get("type") == "json_schema":
        # PI-005 — return content that looks like JSON when json_schema asked.
        message = {
            "role": "assistant",
            "content": '{"answer": "mocked", "confidence": 0.42}',
        }
        finish_reason = "stop"
    else:
        message = {
            "role": "assistant",
            "content": f"Mocked reply to: {user_text[:80]}",
        }
        finish_reason = "stop"

    prompt_tokens = sum(_approx_tokens(str(m.get("content", ""))) for m in messages)
    completion_tokens = _approx_tokens(str(message.get("content") or "tool_call"))

    return {
        "id": _id("chatcmpl"),
        "object": "chat.completion",
        "created": _now(),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
                "logprobs": None,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "system_fingerprint": "fp_mock",
    }


def _stream_chunks_for(req: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the chunk sequence a real OpenAI SSE stream would emit."""
    model = req.get("model", "gpt-4o-mini")
    cmpl_id = _id("chatcmpl")
    text = "Mocked streaming reply."
    words = text.split(" ")
    chunks: list[dict[str, Any]] = []
    base = {
        "id": cmpl_id,
        "object": "chat.completion.chunk",
        "created": _now(),
        "model": model,
    }
    # role-only opener, then per-word delta, then finish_reason close.
    chunks.append(
        {**base, "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]}
    )
    for w in words:
        chunks.append(
            {
                **base,
                "choices": [{"index": 0, "delta": {"content": w + " "}, "finish_reason": None}],
            }
        )
    chunks.append(
        {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
    )
    return chunks


@router.post("/chat/completions")
async def chat_completions(request: Request) -> Any:
    route = "chat"
    body = await request.json()
    maybe_inject_error(PROVIDER, route)
    slept = await sleep_with_jitter(engine.latency_ms(PROVIDER, route))

    if body.get("stream"):
        # NFR-003 — slow_stream scenario tests gateway TTFT/flushing behavior.
        chunks = _stream_chunks_for(body)
        engine.record(latency_ms=slept)
        return EventSourceResponse(stream_chunks(PROVIDER, route, chunks))

    engine.record(latency_ms=slept)
    return _build_chat_response(body)


# ---------------- /v1/embeddings ----------------------------------------------


@router.post("/embeddings")
async def embeddings(request: Request) -> dict[str, Any]:
    route = "embeddings"
    body = await request.json()
    maybe_inject_error(PROVIDER, route)
    slept = await sleep_with_jitter(engine.latency_ms(PROVIDER, route))

    inputs = body.get("input", "")
    if isinstance(inputs, str):
        inputs = [inputs]

    # 1536 dims by default to match text-embedding-3-small. Deterministic-ish
    # values keep snapshot tests reproducible.
    dim = int(body.get("dimensions", 1536))
    data = [
        {
            "object": "embedding",
            "index": i,
            "embedding": [((i + j) % 100) / 100.0 for j in range(dim)],
        }
        for i, _ in enumerate(inputs)
    ]
    prompt_tokens = sum(_approx_tokens(str(t)) for t in inputs)
    engine.record(latency_ms=slept)
    return {
        "object": "list",
        "data": data,
        "model": body.get("model", "text-embedding-3-small"),
        "usage": {"prompt_tokens": prompt_tokens, "total_tokens": prompt_tokens},
    }


# ---------------- /v1/images/generations --------------------------------------


@router.post("/images/generations")
async def images_generations(request: Request) -> dict[str, Any]:
    route = "images"
    body = await request.json()
    maybe_inject_error(PROVIDER, route)
    slept = await sleep_with_jitter(engine.latency_ms(PROVIDER, route))

    n = int(body.get("n", 1))
    response_format = body.get("response_format", "url")
    data: list[dict[str, str]] = []
    for _ in range(n):
        if response_format == "b64_json":
            data.append({"b64_json": _TINY_PNG_B64})
        else:
            data.append({"url": "https://mock.local/openrouter/mock-image.png"})

    engine.record(latency_ms=slept)
    return {"created": _now(), "data": data}


# Quiet ruff F401 — base64 is exposed for future b64 image tests.
_ = base64
