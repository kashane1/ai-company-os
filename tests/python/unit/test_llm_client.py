"""Tests for the OpenRouter chat-model client — offline via httpx.MockTransport."""

from __future__ import annotations

import httpx
import pytest

from packages.tools.llm.client import ModelError, OpenRouterClient


def _client(handler, **kwargs) -> OpenRouterClient:
    transport = httpx.MockTransport(handler)
    return OpenRouterClient(api_key="key_123", client=httpx.Client(transport=transport), **kwargs)


def test_complete_sends_expected_request_and_returns_content() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers["Authorization"]
        captured["url"] = str(request.url)
        import json as _json

        captured["body"] = _json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}]})

    client = _client(handler, model="anthropic/claude-sonnet-4")
    out = client.complete("sys", "usr", temperature=0.0)

    assert out == "hello"
    assert captured["auth"] == "Bearer key_123"
    assert str(captured["url"]).endswith("/chat/completions")
    body = captured["body"]
    assert body["model"] == "anthropic/claude-sonnet-4"
    assert body["temperature"] == 0.0
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["content"] == "usr"


def test_non_200_raises_model_error() -> None:
    client = _client(lambda r: httpx.Response(429, text="rate limited"))
    with pytest.raises(ModelError):
        client.complete("s", "u")


def test_unexpected_shape_raises_model_error() -> None:
    client = _client(lambda r: httpx.Response(200, json={"nope": True}))
    with pytest.raises(ModelError):
        client.complete("s", "u")


def test_missing_api_key_raises() -> None:
    client = OpenRouterClient(api_key="", client=httpx.Client())
    with pytest.raises(ModelError):
        client.complete("s", "u")
