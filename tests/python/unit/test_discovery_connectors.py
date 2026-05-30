"""Connector tests — fully offline via httpx.MockTransport.

No live network: every HTTP call is served by an in-test handler, so these
tests assert the connector's behaviour (pain filtering, provenance, refusal
paths) without depending on Hacker News or GitHub being reachable.
"""

from __future__ import annotations

import httpx
import pytest

from packages.discovery.connectors.base import (
    CompliancePolicyError,
    ConnectorConfig,
    FetchOptions,
)
from packages.discovery.connectors.github import GitHubConnector
from packages.discovery.connectors.hackernews import HackerNewsConnector
from packages.discovery.connectors.rate_limiter import RateLimiter
from packages.discovery.connectors.registry import build_connectors, load_source_configs


def _no_wait_limiter() -> RateLimiter:
    return RateLimiter(600, now=lambda: 0.0, sleep=lambda s: None)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _hn_config(enabled: bool = True) -> ConnectorConfig:
    return ConnectorConfig(id="hackernews", enabled=enabled, endpoint="https://hn.algolia.com/api/v1")


def test_hackernews_keeps_only_pain_signals_with_provenance() -> None:
    payload = {
        "hits": [
            {
                "objectID": "111",
                "title": "Is there a tool that automates invoice resizing?",
                "points": 9,
            },
            {"objectID": "222", "title": "Show HN: my weekend project", "points": 4},
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/search")
        assert request.headers["User-Agent"]  # honest identification
        return httpx.Response(200, json=payload)

    conn = HackerNewsConnector(
        _hn_config(), client=_client(handler), rate_limiter=_no_wait_limiter()
    )
    signals = conn.fetch(FetchOptions(query="resize", limit=10))

    assert len(signals) == 1  # the non-pain "Show HN" is filtered out
    assert signals[0].url == "https://news.ycombinator.com/item?id=111"
    assert "tool" in signals[0].quote.lower()


def test_hackernews_backoff_on_429_returns_empty() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={})

    config = ConnectorConfig(id="hackernews", endpoint="https://hn.algolia.com/api/v1")
    conn = HackerNewsConnector(config, client=_client(handler), rate_limiter=_no_wait_limiter())
    assert conn.fetch(FetchOptions(query="x")) == []


def test_hackernews_refuses_when_disabled() -> None:
    conn = HackerNewsConnector(
        _hn_config(enabled=False), client=_client(lambda r: httpx.Response(200, json={}))
    )
    with pytest.raises(CompliancePolicyError):
        conn.fetch(FetchOptions(query="x"))


def test_hackernews_refuses_bulk_crawl() -> None:
    conn = HackerNewsConnector(_hn_config(), client=_client(lambda r: httpx.Response(200, json={})))
    with pytest.raises(CompliancePolicyError):
        conn.fetch(FetchOptions(query="x", bulk=True))


def test_github_requires_token() -> None:
    config = ConnectorConfig(id="github", auth_env="GITHUB_TOKEN")
    conn = GitHubConnector(config, client=_client(lambda r: httpx.Response(200, json={})), token="")
    ok, detail = conn.healthcheck()
    assert ok is False
    with pytest.raises(CompliancePolicyError):
        conn.fetch(FetchOptions(query="x"))


def test_github_fetches_issue_pain_with_token() -> None:
    payload = {
        "items": [
            {
                "title": "Wish there was an alternative to the manual export step",
                "body": "I hate doing this manually every release",
                "html_url": "https://github.com/acme/repo/issues/7",
                "state": "open",
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer tok_123"
        return httpx.Response(200, json=payload)

    config = ConnectorConfig(id="github", auth_env="GITHUB_TOKEN")
    conn = GitHubConnector(
        config, client=_client(handler), rate_limiter=_no_wait_limiter(), token="tok_123"
    )
    signals = conn.fetch(FetchOptions(query="manual"))
    assert len(signals) == 1
    assert signals[0].url == "https://github.com/acme/repo/issues/7"


def test_registry_loads_shipped_sources() -> None:
    configs = {c.id: c for c in load_source_configs()}
    assert configs["hackernews"].enabled is True
    assert configs["hackernews"].rate_limit.requests_per_minute == 60  # source override merged
    assert configs["github"].auth_env == "GITHUB_TOKEN"
    assert configs["reddit"].enabled is True  # OAuth connector now wired (E4)
    assert configs["producthunt"].enabled is False  # still stubbed


def test_registry_builds_only_enabled_known_connectors() -> None:
    client = _client(lambda r: httpx.Response(200, json={"hits": []}))
    connectors = build_connectors(client=client)
    assert set(connectors) == {"hackernews", "github", "reddit"}
    assert connectors["hackernews"].id == "hackernews"
