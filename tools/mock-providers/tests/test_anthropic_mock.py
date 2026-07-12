"""Cover the Anthropic mock surface — content blocks, tool_use, streaming events."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_messages_text_block(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "message"
    assert body["content"][0]["type"] == "text"
    assert body["stop_reason"] == "end_turn"


@pytest.mark.asyncio
async def test_messages_tool_use(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "use a tool"}],
            "tools": [{"name": "lookup", "input_schema": {"type": "object"}}],
        },
    )
    body = r.json()
    assert body["content"][0]["type"] == "tool_use"
    assert body["stop_reason"] == "tool_use"


@pytest.mark.asyncio
async def test_messages_streaming_events(client: AsyncClient) -> None:
    async with client.stream(
        "POST",
        "/v1/messages",
        json={
            "model": "claude-3-5-sonnet-20241022",
            "stream": True,
            "messages": [{"role": "user", "content": "stream"}],
        },
    ) as resp:
        assert resp.status_code == 200
        body = b""
        async for chunk in resp.aiter_bytes():
            body += chunk
    # Anthropic uses typed events; we should see at least message_start + stop.
    assert b"message_start" in body
    assert b"message_stop" in body
