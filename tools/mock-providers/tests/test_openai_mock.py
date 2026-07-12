"""Cover the OpenAI mock surface — non-stream, stream, tools, embeddings, images."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_completion_non_streaming_shape(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/chat/completions",
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["finish_reason"] == "stop"
    assert "usage" in body and body["usage"]["total_tokens"] > 0


@pytest.mark.asyncio
async def test_chat_completion_tool_calls(client: AsyncClient) -> None:
    """PI-004 — when tools are advertised, mock returns a tool_calls reply."""
    r = await client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "use a tool"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "lookup", "parameters": {"type": "object"}},
                }
            ],
        },
    )
    assert r.status_code == 200
    msg = r.json()["choices"][0]["message"]
    assert msg["content"] is None
    assert msg["tool_calls"][0]["function"]["name"] == "lookup"


@pytest.mark.asyncio
async def test_chat_completion_streaming_emits_done(client: AsyncClient) -> None:
    """GW-002 — SSE stream must terminate with `data: [DONE]`."""
    async with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "stream": True,
            "messages": [{"role": "user", "content": "stream"}],
        },
    ) as resp:
        assert resp.status_code == 200
        body = b""
        async for chunk in resp.aiter_bytes():
            body += chunk
    assert b"data: [DONE]" in body
    assert b"chat.completion.chunk" in body


@pytest.mark.asyncio
async def test_embeddings_returns_requested_dimensions(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/embeddings",
        json={"model": "text-embedding-3-small", "input": ["hello", "world"], "dimensions": 8},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 2
    assert len(data[0]["embedding"]) == 8


@pytest.mark.asyncio
async def test_images_generations_url_response(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/images/generations",
        json={"model": "dall-e-3", "prompt": "a cat", "n": 2},
    )
    assert r.status_code == 200
    assert len(r.json()["data"]) == 2
    assert r.json()["data"][0]["url"].startswith("https://")
