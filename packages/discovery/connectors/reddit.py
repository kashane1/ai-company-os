"""Reddit connector via the official OAuth API (application-only).

Reddit is the highest-signal source for "is there a tool that…" pain, but it
requires OAuth. This uses the **client-credentials** (app-only) grant: a
confidential "script"/"web" app's client id + secret exchange for a read-only
bearer token — no user password, enough to search public posts within quota.

Why app-only over password grant: it needs no human credentials in the
connector, keeps the blast radius small (read-only), and is the right fit for an
unattended worker. Tokens are cached until just before expiry.

Compliance, same as the other connectors: official API only (no HTML scraping),
honest User-Agent, rate-limited with backoff, provenance on every signal, and a
refusal to run without credentials rather than hammering an anonymous endpoint.

The HTTP client + clock are injectable so the whole thing — token fetch, caching,
search, backoff — is tested offline via ``httpx.MockTransport``.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Callable

import httpx

from packages.config.settings import (
    REDDIT_CLIENT_ID_ENV_VAR,
    REDDIT_CLIENT_SECRET_ENV_VAR,
)
from packages.discovery.connectors._pain import classify, looks_like_pain
from packages.discovery.connectors.base import (
    CompliancePolicyError,
    ConnectorConfig,
    FetchOptions,
    RawSignal,
)
from packages.discovery.connectors.rate_limiter import RateLimiter

OAUTH_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
DEFAULT_API_URL = "https://oauth.reddit.com"
_TOKEN_SAFETY_MARGIN_SECONDS = 60


class RedditConnector:
    id = "reddit"

    def __init__(
        self,
        config: ConnectorConfig,
        *,
        client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.config = config
        self._endpoint = config.endpoint or DEFAULT_API_URL
        self._client = client or httpx.Client(timeout=10.0)
        self._limiter = rate_limiter or RateLimiter(config.rate_limit.requests_per_minute)
        self._client_id = (
            client_id if client_id is not None else os.environ.get(REDDIT_CLIENT_ID_ENV_VAR, "")
        )
        self._client_secret = (
            client_secret
            if client_secret is not None
            else os.environ.get(REDDIT_CLIENT_SECRET_ENV_VAR, "")
        )
        self._now = now or time.monotonic
        self._token: str | None = None
        self._token_expiry = 0.0

    def _has_credentials(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def _access_token(self) -> str:
        now = self._now()
        if self._token and now < self._token_expiry:
            return self._token
        response = self._client.post(
            OAUTH_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
            headers={"User-Agent": self.config.user_agent},
        )
        if response.status_code != 200:
            raise CompliancePolicyError(
                f"reddit token request failed ({response.status_code})"
            )
        data = response.json()
        self._token = str(data["access_token"])
        ttl = float(data.get("expires_in", 3600)) - _TOKEN_SAFETY_MARGIN_SECONDS
        self._token_expiry = now + ttl
        return self._token

    def fetch(self, options: FetchOptions) -> list[RawSignal]:
        if not self.config.enabled:
            raise CompliancePolicyError(
                f"connector {self.id} is disabled in config/sources.yaml"
            )
        if options.bulk and not options.authorized:
            raise CompliancePolicyError(
                "bulk crawl requires an approved bulk_crawl gate (authorized=True)"
            )
        if not self._has_credentials():
            raise CompliancePolicyError(
                f"reddit connector needs ${REDDIT_CLIENT_ID_ENV_VAR} and "
                f"${REDDIT_CLIENT_SECRET_ENV_VAR}; refusing to use an anonymous endpoint"
            )

        self._limiter.acquire()
        token = self._access_token()
        limit = min(max(1, options.limit), 100)
        response = self._client.get(
            f"{self._endpoint}/search",
            params={"q": options.query, "limit": limit, "sort": "relevance", "type": "link"},
            headers={"Authorization": f"Bearer {token}", "User-Agent": self.config.user_agent},
        )
        if response.status_code in self.config.rate_limit.backoff_on:
            self._limiter.backoff()
            return []
        response.raise_for_status()

        captured_at = datetime.now(timezone.utc).isoformat()
        signals: list[RawSignal] = []
        children = response.json().get("data", {}).get("children", [])
        for child in children:
            post = child.get("data", {})
            text = f"{post.get('title', '')} {post.get('selftext', '')}".strip()
            if not text or not looks_like_pain(text):
                continue
            permalink = post.get("permalink", "")
            signals.append(
                RawSignal(
                    text=str(post.get("title") or text)[:280],
                    url=f"https://www.reddit.com{permalink}",
                    kind=classify(text),
                    quote=str(post.get("selftext") or post.get("title") or "")[:240],
                    captured_at=captured_at,
                    meta={
                        "subreddit": post.get("subreddit"),
                        "score": post.get("score"),
                        "num_comments": post.get("num_comments"),
                    },
                )
            )
        return signals

    def healthcheck(self) -> tuple[bool, str]:
        if not self._has_credentials():
            return (False, f"missing ${REDDIT_CLIENT_ID_ENV_VAR}/${REDDIT_CLIENT_SECRET_ENV_VAR}")
        try:
            self._access_token()
            return (True, "token acquired")
        except Exception as exc:  # pragma: no cover - network failure path
            return (False, str(exc))
