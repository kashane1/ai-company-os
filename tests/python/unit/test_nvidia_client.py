"""Tests for the NVIDIA NIM client + registry — offline via httpx.MockTransport."""

from __future__ import annotations

import json

import httpx
import pytest

from packages.tools.llm import (
    ChatResult,
    ModelError,
    NvidiaClient,
    available_providers,
    build_chat_model,
)
from packages.tools.llm.nvidia import _iter_sse_content, _parse_chat_result


def _client(handler, **kwargs) -> NvidiaClient:
    transport = httpx.MockTransport(handler)
    return NvidiaClient(api_key="key_123", client=httpx.Client(transport=transport), **kwargs)


# ── complete() — the ChatModel protocol surface ──────────────────────────────
def test_complete_sends_expected_request_and_returns_content() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers["Authorization"]
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}]})

    client = _client(handler, model="meta/llama-3.3-70b-instruct")
    out = client.complete("sys", "usr", temperature=0.0)

    assert out == "hello"
    assert captured["auth"] == "Bearer key_123"
    assert str(captured["url"]).endswith("/chat/completions")
    body = captured["body"]
    assert body["model"] == "meta/llama-3.3-70b-instruct"
    assert body["temperature"] == 0.0
    assert body["stream"] is False
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["content"] == "usr"


def test_default_model_is_used_when_unspecified() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    _client(handler).complete("s", "u")
    assert captured["body"]["model"] == "meta/llama-3.3-70b-instruct"


# ── chat() — structured result + reasoning controls ──────────────────────────
def test_chat_returns_structured_result_with_reasoning_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "nvidia/nemotron",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": "9.9 is larger",
                            "reasoning_content": "compare 0.11 vs 0.9",
                        },
                    }
                ],
                "usage": {"total_tokens": 42},
            },
        )

    result = _client(handler).chat([{"role": "user", "content": "9.11 or 9.9?"}])
    assert isinstance(result, ChatResult)
    assert result.content == "9.9 is larger"
    assert result.reasoning_content == "compare 0.11 vs 0.9"
    assert result.finish_reason == "stop"
    assert result.usage["total_tokens"] == 42
    assert result.raw["model"] == "nvidia/nemotron"


def test_chat_reasoning_kwargs_land_in_extra_body() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]})

    _client(handler).chat(
        [{"role": "user", "content": "hi"}],
        top_p=0.95,
        max_tokens=128,
        stop=["END"],
        enable_thinking=True,
        reasoning_budget=4096,
    )
    body = captured["body"]
    assert body["top_p"] == 0.95
    assert body["max_tokens"] == 128
    assert body["stop"] == ["END"]
    assert body["chat_template_kwargs"] == {"enable_thinking": True}
    assert body["reasoning_budget"] == 4096


# ── embeddings ───────────────────────────────────────────────────────────────
def test_embed_returns_vectors_in_index_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/embeddings")
        return httpx.Response(
            200,
            json={"data": [
                {"index": 1, "embedding": [0.3, 0.4]},
                {"index": 0, "embedding": [0.1, 0.2]},
            ]},
        )

    vectors = _client(handler).embed(["a", "b"])
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_embed_accepts_single_string() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0]}]})

    out = _client(handler).embed("solo", input_type="passage")
    assert out == [[1.0]]
    assert captured["body"]["input"] == ["solo"]
    assert captured["body"]["input_type"] == "passage"


# ── error handling (mirrors OpenRouter client) ───────────────────────────────
def test_non_200_raises_model_error() -> None:
    client = _client(lambda r: httpx.Response(429, text="rate limited"))
    with pytest.raises(ModelError):
        client.complete("s", "u")


def test_unexpected_shape_raises_model_error() -> None:
    client = _client(lambda r: httpx.Response(200, json={"nope": True}))
    with pytest.raises(ModelError):
        client.complete("s", "u")


def test_missing_api_key_raises() -> None:
    client = NvidiaClient(api_key="", client=httpx.Client())
    with pytest.raises(ModelError):
        client.complete("s", "u")


# ── streaming + SSE parser (pure) ────────────────────────────────────────────
def test_sse_parser_yields_content_deltas_and_stops_on_done() -> None:
    lines = [
        'data: {"choices":[{"delta":{"content":"Hel"}}]}',
        "",  # keepalive / blank
        'data: {"choices":[{"delta":{"content":"lo"}}]}',
        'data: {"choices":[{"delta":{"role":"assistant"}}]}',  # no content -> skipped
        "data: [DONE]",
        'data: {"choices":[{"delta":{"content":"ignored after done"}}]}',
    ]
    assert list(_iter_sse_content(lines)) == ["Hel", "lo"]


def test_chat_stream_yields_pieces() -> None:
    body = (
        'data: {"choices":[{"delta":{"content":"a"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"b"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, text=body)

    pieces = list(_client(handler).chat_stream([{"role": "user", "content": "hi"}]))
    assert pieces == ["a", "b"]


# ── parser unit: missing content is a typed error ────────────────────────────
def test_parse_chat_result_missing_content_raises() -> None:
    with pytest.raises(ModelError):
        _parse_chat_result({"choices": [{"message": {"role": "assistant"}}]})


# ── registry / connector seam ────────────────────────────────────────────────
def test_build_chat_model_returns_nvidia_client() -> None:
    model = build_chat_model("nvidia")
    assert isinstance(model, NvidiaClient)
    assert model.model == "meta/llama-3.3-70b-instruct"


def test_build_chat_model_reasoning_variant() -> None:
    model = build_chat_model("nvidia:reasoning")
    assert isinstance(model, NvidiaClient)
    assert "reasoning" in model.model


def test_build_chat_model_unknown_provider_raises() -> None:
    with pytest.raises(ModelError):
        build_chat_model("does-not-exist")


def test_available_providers_lists_nvidia() -> None:
    providers = available_providers()
    assert "nvidia" in providers
    assert "nvidia:reasoning" in providers
    assert "openrouter" in providers
