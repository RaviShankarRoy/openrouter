"""Google AI mock — `/v1beta/models/{model}:generateContent`.

Mirrors `google-genai`'s REST shape: parts/inlineData content blocks, candidates
with finishReason, usageMetadata with token counts.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from src.scenarios import engine
from src.scenarios.errors import maybe_inject_error
from src.scenarios.latency import sleep_with_jitter

router = APIRouter()
PROVIDER = "google"


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _extract_user_text(req: dict[str, Any]) -> str:
    contents = req.get("contents", [])
    for c in reversed(contents):
        for part in c.get("parts", []):
            if "text" in part:
                return str(part["text"])
    return ""


@router.post("/models/{model}:generateContent")
async def generate_content(model: str, request: Request) -> dict[str, Any]:
    route = "generateContent"
    body = await request.json()
    maybe_inject_error(PROVIDER, route)
    slept = await sleep_with_jitter(engine.latency_ms(PROVIDER, route))

    user_text = _extract_user_text(body)
    text = f"Mocked Gemini reply to: {user_text[:80]}"

    prompt_tokens = sum(
        _approx_tokens(p.get("text", ""))
        for c in body.get("contents", [])
        for p in c.get("parts", [])
    )
    candidates_tokens = _approx_tokens(text)

    engine.record(latency_ms=slept)
    return {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": text}]},
                "finishReason": "STOP",
                "index": 0,
                "safetyRatings": [],
            }
        ],
        "usageMetadata": {
            "promptTokenCount": prompt_tokens,
            "candidatesTokenCount": candidates_tokens,
            "totalTokenCount": prompt_tokens + candidates_tokens,
        },
        "modelVersion": model,
    }


# Streaming variant — Google uses chunked JSON, not SSE; emulate enough to
# unblock adapter tests that touch GW-002 via the google adapter.
@router.post("/models/{model}:streamGenerateContent")
async def stream_generate_content(model: str, request: Request) -> dict[str, Any]:
    # Tests that exercise streaming go through the OpenAI/Anthropic mocks; this
    # endpoint just returns a non-streaming chunk so adapter selection works.
    return await generate_content(model, request)
