"""Hacker News connector via the official Algolia HN Search API.

Why this one ships as the reference connector: the HN Search API is public,
documented, generous, and needs no auth — so it is the cleanest example of a
compliant source (official API, honest User-Agent, rate-limited, provenance on
every signal) without any ToS grey area.

The HTTP client is injected so tests run fully offline via
``httpx.MockTransport``.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from packages.discovery.connectors._pain import classify, looks_like_pain
from packages.discovery.connectors.base import (
    CompliancePolicyError,
    ConnectorConfig,
    FetchOptions,
    RawSignal,
)
from packages.discovery.connectors.rate_limiter import RateLimiter

DEFAULT_ENDPOINT = "https://hn.algolia.com/api/v1"


class HackerNewsConnector:
    id = "hackernews"

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.config = config
        self._endpoint = config.endpoint or DEFAULT_ENDPOINT
        self._client = client or httpx.Client(timeout=10.0)
        self._limiter = rate_limiter or RateLimiter(config.rate_limit.requests_per_minute)

    def fetch(self, options: FetchOptions) -> list[RawSignal]:
        if not self.config.enabled:
            raise CompliancePolicyError(
                f"connector {self.id} is disabled in config/sources.yaml"
            )
        if options.bulk and not options.authorized:
            # Bulk crawls are a gated action; the connector refuses unless the
            # caller has passed the bulk_crawl approval gate (sets authorized).
            raise CompliancePolicyError(
                "bulk crawl requires an approved bulk_crawl gate (authorized=True)"
            )

        self._limiter.acquire()
        limit = min(max(1, options.limit), 100)
        response = self._client.get(
            f"{self._endpoint}/search",
            params={"query": options.query, "tags": "(story,comment)", "hitsPerPage": limit},
            headers={"User-Agent": self.config.user_agent},
        )

        if response.status_code in self.config.rate_limit.backoff_on:
            self._limiter.backoff()
            return []
        response.raise_for_status()

        captured_at = datetime.now(timezone.utc).isoformat()
        signals: list[RawSignal] = []
        for hit in response.json().get("hits", []):
            parts = (hit.get("title"), hit.get("story_text"), hit.get("comment_text"))
            text = " ".join(part for part in parts if part).strip()
            if not text or not looks_like_pain(text):
                continue
            object_id = hit.get("objectID", "")
            signals.append(
                RawSignal(
                    text=(hit.get("title") or text)[:280],
                    url=f"https://news.ycombinator.com/item?id={object_id}",
                    kind=classify(text),
                    quote=text[:240],
                    captured_at=captured_at,
                    meta={
                        "points": hit.get("points"),
                        "num_comments": hit.get("num_comments"),
                        "author": hit.get("author"),
                        "external_url": hit.get("url"),
                    },
                )
            )
        return signals

    def healthcheck(self) -> tuple[bool, str]:
        try:
            self._limiter.acquire()
            response = self._client.get(
                f"{self._endpoint}/search",
                params={"query": "test", "hitsPerPage": 1},
                headers={"User-Agent": self.config.user_agent},
            )
            return (response.status_code == 200, f"status={response.status_code}")
        except Exception as exc:  # pragma: no cover - network failure path
            return (False, str(exc))
