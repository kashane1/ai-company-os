"""GitHub connector via the official Search Issues API.

Good for "awesome-x" gaps, recurring issue pain, and abandoned tools. Uses the
authenticated REST API within quota (no scraping). The token is read from the
env var named in ``config.auth_env`` (default ``GITHUB_TOKEN``); without it the
connector reports unhealthy and refuses to fetch rather than hitting the low
anonymous rate limit.

The HTTP client is injected so tests run fully offline via
``httpx.MockTransport``.
"""

from __future__ import annotations

import os
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

DEFAULT_ENDPOINT = "https://api.github.com"


class GitHubConnector:
    id = "github"

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        token: str | None = None,
    ) -> None:
        self.config = config
        self._endpoint = config.endpoint or DEFAULT_ENDPOINT
        self._client = client or httpx.Client(timeout=10.0)
        self._limiter = rate_limiter or RateLimiter(config.rate_limit.requests_per_minute)
        self._auth_env = config.auth_env or "GITHUB_TOKEN"
        self._token = token if token is not None else os.environ.get(self._auth_env, "")

    def _headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "application/vnd.github+json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def fetch(self, options: FetchOptions) -> list[RawSignal]:
        if not self.config.enabled:
            raise CompliancePolicyError(
                f"connector {self.id} is disabled in config/sources.yaml"
            )
        if options.bulk and not options.authorized:
            raise CompliancePolicyError(
                "bulk crawl requires an approved bulk_crawl gate (authorized=True)"
            )
        if not self._token:
            raise CompliancePolicyError(
                f"github connector needs a token in ${self._auth_env}; "
                "refusing to use the anonymous quota"
            )

        self._limiter.acquire()
        limit = min(max(1, options.limit), 100)
        response = self._client.get(
            f"{self._endpoint}/search/issues",
            params={"q": options.query, "per_page": limit, "sort": "updated"},
            headers=self._headers(),
        )

        if response.status_code in self.config.rate_limit.backoff_on:
            self._limiter.backoff()
            return []
        response.raise_for_status()

        captured_at = datetime.now(timezone.utc).isoformat()
        signals: list[RawSignal] = []
        for item in response.json().get("items", []):
            text = " ".join(part for part in (item.get("title"), item.get("body")) if part).strip()
            if not text or not looks_like_pain(text):
                continue
            signals.append(
                RawSignal(
                    text=(item.get("title") or text)[:280],
                    url=str(item.get("html_url", "")),
                    kind=classify(text),
                    quote=text[:240],
                    captured_at=captured_at,
                    meta={
                        "state": item.get("state"),
                        "comments": item.get("comments"),
                        "repository_url": item.get("repository_url"),
                    },
                )
            )
        return signals

    def healthcheck(self) -> tuple[bool, str]:
        if not self._token:
            return (False, f"missing ${self._auth_env}")
        return (True, "token present")
