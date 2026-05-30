"""Reddit connector tests — offline via httpx.MockTransport.

The mock handler serves both the OAuth token endpoint and the search endpoint by
path, so token fetch, caching, search parsing, and refusal paths are all covered
with no network and no real credentials.
"""

from __future__ import annotations

import httpx
import pytest

from packages.discovery.connectors.base import (
    CompliancePolicyError,
    ConnectorConfig,
    FetchOptions,
)
from packages.discovery.connectors.rate_limiter import RateLimiter
from packages.discovery.connectors.reddit import RedditConnector


def _no_wait_limiter() -> RateLimiter:
    return RateLimiter(600, now=lambda: 0.0, sleep=lambda s: None)


def _config(enabled: bool = True) -> ConnectorConfig:
    return ConnectorConfig(id="reddit", enabled=enabled, endpoint="https://oauth.reddit.com")


SEARCH_PAYLOAD = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "Is there a tool that automates X?",
                    "selftext": "I do this manually every week",
                    "permalink": "/r/SaaS/comments/abc/",
                    "subreddit": "SaaS",
                    "score": 42,
                    "num_comments": 7,
                }
            },
            {"data": {"title": "Just sharing my launch", "permalink": "/r/x/1", "subreddit": "x"}},
        ]
    }
}


def _handler(token_calls: list[int] | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/access_token"):
            if token_calls is not None:
                token_calls.append(1)
            assert request.headers["Authorization"].startswith("Basic ")  # client_id:secret
            return httpx.Response(200, json={"access_token": "tok_abc", "expires_in": 3600})
        if request.url.path.endswith("/search"):
            assert request.headers["Authorization"] == "Bearer tok_abc"
            return httpx.Response(200, json=SEARCH_PAYLOAD)
        return httpx.Response(404)

    return handler


def _connector(handler, **kwargs) -> RedditConnector:
    return RedditConnector(
        _config(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        rate_limiter=_no_wait_limiter(),
        client_id="cid",
        client_secret="secret",
        **kwargs,
    )


def test_fetch_returns_only_pain_with_provenance() -> None:
    conn = _connector(_handler())
    signals = conn.fetch(FetchOptions(query="automate", limit=10))
    assert len(signals) == 1  # the "just sharing" post is filtered out
    assert signals[0].url == "https://www.reddit.com/r/SaaS/comments/abc/"
    assert signals[0].meta["subreddit"] == "SaaS"


def test_token_is_cached_across_fetches() -> None:
    calls: list[int] = []
    conn = _connector(_handler(calls), now=lambda: 0.0)
    conn.fetch(FetchOptions(query="a"))
    conn.fetch(FetchOptions(query="b"))
    assert len(calls) == 1  # token fetched once, reused while unexpired


def test_refuses_without_credentials() -> None:
    conn = RedditConnector(
        _config(),
        client=httpx.Client(transport=httpx.MockTransport(_handler())),
        rate_limiter=_no_wait_limiter(),
        client_id="",
        client_secret="",
    )
    ok, _ = conn.healthcheck()
    assert ok is False
    with pytest.raises(CompliancePolicyError):
        conn.fetch(FetchOptions(query="x"))


def test_refuses_when_disabled() -> None:
    conn = RedditConnector(
        _config(enabled=False),
        client=httpx.Client(transport=httpx.MockTransport(_handler())),
        client_id="cid",
        client_secret="secret",
    )
    with pytest.raises(CompliancePolicyError):
        conn.fetch(FetchOptions(query="x"))


def test_unauthorized_bulk_is_refused_but_authorized_allowed() -> None:
    conn = _connector(_handler())
    with pytest.raises(CompliancePolicyError):
        conn.fetch(FetchOptions(query="x", bulk=True))
    # With authorization (gate passed), the same bulk fetch proceeds.
    signals = conn.fetch(FetchOptions(query="x", bulk=True, authorized=True))
    assert len(signals) == 1


def test_backoff_on_429_returns_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/access_token"):
            return httpx.Response(200, json={"access_token": "tok_abc", "expires_in": 3600})
        return httpx.Response(429)

    conn = _connector(handler)
    assert conn.fetch(FetchOptions(query="x")) == []
