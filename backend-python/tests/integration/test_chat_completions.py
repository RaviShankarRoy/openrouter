"""Integration: provider adapters against mocked HTTP via respx.

This validates the OpenAIAdapter end-to-end without hitting the real API.
"""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.repository.providers.base import UnifiedRequest
from app.repository.providers.openai_adapter import OpenAIAdapter


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_openai_complete_translates_response(respx_mock: respx.Router) -> None:
    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(
            200,
            json={
                "id": "chatcmpl-fake",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "hello back"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )
    )
    adapter = OpenAIAdapter()
    resp = await adapter.complete(
        UnifiedRequest(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
        )
    )
    assert resp.content == "hello back"
    assert resp.finish_reason == "stop"
    assert resp.usage.input == 5
    assert resp.usage.output == 2


@pytest.mark.asyncio
async def test_openai_count_tokens_uses_tiktoken() -> None:
    adapter = OpenAIAdapter()
    n = await adapter.count_tokens(
        "gpt-4o-mini",
        [{"role": "user", "content": "Hello world, this is a tokenization test."}],
    )
    assert n > 0
