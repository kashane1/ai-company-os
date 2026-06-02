"""HTTP website checks for prospecting.

Classification is deliberately simple in Phase 1:

* ``ok_owned``: request succeeds and final host is not a known social/marketplace
  host and the body does not look parked.
* ``redirect_social``: final URL lands on social or marketplace infrastructure,
  meaning the prospect still lacks an owned site for cohort purposes.
* ``dead``: HTTP status is 4xx/5xx.
* ``parked``: body/title contains common parked-domain phrases.
* ``timeout`` / ``error``: network failure classes from httpx.

For records with no URL, the queue rule still says the no-site signal should be
considered; the actual HTTP fetch is impossible and is stored as ``skipped``.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Callable

import httpx

from packages.discovery.connectors.rate_limiter import RateLimiter
from packages.prospecting.config import HttpConfig
from packages.prospecting.connectors.google_places import MARKETPLACE_HOSTS, SOCIAL_HOSTS, normalized_host
from packages.schemas.prospect import HttpCheck, HttpCheckClass, MapsWebsiteClass, ProspectRecord

PARKED_MARKERS = (
    "domain is for sale",
    "this domain is for sale",
    "buy this domain",
    "sedo",
    "afternic",
    "parkingcrew",
    "domain parking",
)


class HTTPChecker:
    def __init__(
        self,
        *,
        config: HttpConfig | None = None,
        client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        now: Callable[[], datetime] | None = None,
        max_attempts: int = 2,
    ) -> None:
        self._config = config or HttpConfig()
        self._client = client or httpx.Client(
            timeout=self._config.timeout_seconds,
            follow_redirects=True,
            max_redirects=self._config.max_redirects,
            headers={"User-Agent": "ai-company-os-prospecting/1.0"},
        )
        self._limiter = rate_limiter or RateLimiter(self._config.per_host_rpm)
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._max_attempts = max(1, max_attempts)

    def check(self, url: str) -> HttpCheck:
        if not url:
            return HttpCheck(HttpCheckClass.SKIPPED, checked_at=self._timestamp())
        last_timeout: httpx.TimeoutException | None = None
        last_error: httpx.RequestError | None = None
        response: httpx.Response | None = None
        for _ in range(self._max_attempts):
            try:
                self._limiter.acquire()
                response = self._client.get(url)
                break
            except httpx.TimeoutException as exc:
                last_timeout = exc
            except httpx.RequestError as exc:
                last_error = exc
        if response is None:
            if last_timeout is not None:
                return HttpCheck(
                    HttpCheckClass.TIMEOUT, checked_at=self._timestamp(), error=str(last_timeout)
                )
            if last_error is not None:
                return HttpCheck(
                    HttpCheckClass.ERROR, checked_at=self._timestamp(), error=str(last_error)
                )
            return HttpCheck(HttpCheckClass.ERROR, checked_at=self._timestamp(), error="no response")
        final_url = str(response.url)
        host = normalized_host(final_url)
        if response.status_code >= 400:
            cls = HttpCheckClass.DEAD
        elif _host_in(host, SOCIAL_HOSTS) or _host_in(host, MARKETPLACE_HOSTS):
            cls = HttpCheckClass.REDIRECT_SOCIAL
        elif _looks_parked(response.text):
            cls = HttpCheckClass.PARKED
        else:
            cls = HttpCheckClass.OK_OWNED
        return HttpCheck(
            http_check_class=cls,
            final_url=final_url,
            status=response.status_code,
            checked_at=self._timestamp(),
        )

    def _timestamp(self) -> str:
        return self._now().isoformat()


def should_check_http(record: ProspectRecord) -> bool:
    if record.maps_website_class in {
        MapsWebsiteClass.ABSENT,
        MapsWebsiteClass.SOCIAL_ONLY,
        MapsWebsiteClass.MARKETPLACE,
    }:
        return True
    digest = hashlib.sha1(record.place_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100 < 5


def _looks_parked(text: str) -> bool:
    lowered = text[:5000].lower()
    return any(marker in lowered for marker in PARKED_MARKERS)


def _host_in(host: str, candidates: set[str]) -> bool:
    return any(host == candidate or host.endswith(f".{candidate}") for candidate in candidates)
