"""HTTP website checks for prospecting.

Classification is deliberately simple in Phase 1:

* ``ok_owned``: request succeeds and final host is not a known social/marketplace
  host and the body does not look parked. Also covers *access-blocked* responses
  (401/403/406/429/451/503): the server answered with a gate, so the site
  demonstrably exists — it is an owned site we just can't crawl, not a dead one.
* ``redirect_social``: final URL lands on social or marketplace infrastructure,
  meaning the prospect still lacks an owned site for cohort purposes.
* ``dead``: HTTP status is a genuine gone/broken code (404/410, or 4xx/5xx that
  is not an access gate after retries). NOT every 4xx/5xx — WAFs (Cloudflare,
  Wix, GoDaddy) routinely 403/503 a non-browser client on a perfectly live site.
* ``parked``: body/title contains common parked-domain phrases.
* ``timeout`` / ``error``: network failure classes from httpx.

We send realistic browser headers so WAF-protected small-business sites are not
mis-flagged as dead, and retry transient status codes before classifying.

For records with no URL, the queue rule still says the no-site signal should be
considered; the actual HTTP fetch is impossible and is stored as ``skipped``.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Callable

import httpx

from packages.discovery.connectors.rate_limiter import RateLimiter
from packages.policies.url_guard import Resolver, is_safe_public_url
from packages.prospecting.config import HttpConfig
from packages.prospecting.connectors.google_places import (
    MARKETPLACE_HOSTS,
    SOCIAL_HOSTS,
    normalized_host,
)
from packages.schemas.prospect import HttpCheck, HttpCheckClass, MapsWebsiteClass, ProspectRecord

# Match genuine parked/for-sale pages. Use specific phrases and the parking
# services' own host/page tokens — NOT bare brand substrings like "sedo", which
# false-match inside live small-business pages ("based on", inline scripts, etc.).
PARKED_MARKERS = (
    "domain is for sale",
    "this domain is for sale",
    "buy this domain",
    "the domain you've entered",
    "domain parking",
    "sedoparking",
    "parkingcrew.net",
    "afternic.com",
    "hugedomains",
    "dan.com",
    "bodis.com",
)

# Look like a real browser. A bot User-Agent gets 403/503'd by Cloudflare/Wix/
# GoDaddy WAFs on live sites, which we used to mis-classify as ``dead``.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Transient statuses worth a retry before we judge the site.
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

# The server answered with an access gate — it is up and the site exists. Treat
# as a live owned site (not stale/dead) for cohort purposes.
ACCESS_BLOCKED_STATUSES = frozenset({401, 403, 406, 429, 451, 503})


class HTTPChecker:
    def __init__(
        self,
        *,
        config: HttpConfig | None = None,
        client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        now: Callable[[], datetime] | None = None,
        max_attempts: int = 2,
        enforce_public_url: bool = True,
        url_resolver: Resolver | None = None,
    ) -> None:
        self._config = config or HttpConfig()
        self._client = client or httpx.Client(
            timeout=self._config.timeout_seconds,
            follow_redirects=True,
            max_redirects=self._config.max_redirects,
            headers=dict(BROWSER_HEADERS),
        )
        self._limiter = rate_limiter or RateLimiter(self._config.per_host_rpm)
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._max_attempts = max(1, max_attempts)
        self._enforce_public_url = enforce_public_url
        self._url_resolver = url_resolver

    def _url_safe(self, url: str) -> bool:
        if not self._enforce_public_url:
            return True
        if self._url_resolver is not None:
            return is_safe_public_url(url, resolver=self._url_resolver)
        return is_safe_public_url(url)

    def check(self, url: str) -> HttpCheck:
        if not url:
            return HttpCheck(HttpCheckClass.SKIPPED, checked_at=self._timestamp())
        # SSRF guard: never fetch a URL pointing at a non-public host (todo 065).
        if not self._url_safe(url):
            return HttpCheck(
                HttpCheckClass.ERROR, checked_at=self._timestamp(), error="blocked: non-public URL"
            )
        last_timeout: httpx.TimeoutException | None = None
        last_error: httpx.RequestError | None = None
        response: httpx.Response | None = None
        for attempt in range(self._max_attempts):
            try:
                self._limiter.acquire()
                response = self._client.get(url, headers=dict(BROWSER_HEADERS))
            except httpx.TimeoutException as exc:
                last_timeout = exc
                response = None
                continue
            except httpx.RequestError as exc:
                last_error = exc
                response = None
                continue
            # Retry transient statuses (rate limits, gateway/5xx) before judging.
            if response.status_code in RETRY_STATUSES and attempt < self._max_attempts - 1:
                continue
            break
        if response is None:
            if last_timeout is not None:
                return HttpCheck(
                    HttpCheckClass.TIMEOUT, checked_at=self._timestamp(), error=str(last_timeout)
                )
            if last_error is not None:
                return HttpCheck(
                    HttpCheckClass.ERROR, checked_at=self._timestamp(), error=str(last_error)
                )
            return HttpCheck(
                HttpCheckClass.ERROR,
                checked_at=self._timestamp(),
                error="no response",
            )
        final_url = str(response.url)
        # Defense-in-depth: a public URL can redirect to an internal host.
        if not self._url_safe(final_url):
            return HttpCheck(
                HttpCheckClass.ERROR,
                checked_at=self._timestamp(),
                error="blocked: redirect to non-public host",
            )
        host = normalized_host(final_url)
        status = response.status_code
        if status < 400:
            if _host_in(host, SOCIAL_HOSTS) or _host_in(host, MARKETPLACE_HOSTS):
                cls = HttpCheckClass.REDIRECT_SOCIAL
            elif _looks_parked(response.text):
                cls = HttpCheckClass.PARKED
            else:
                cls = HttpCheckClass.OK_OWNED
        elif status in ACCESS_BLOCKED_STATUSES:
            # Server is up but gating us (WAF/auth/rate limit) — the site exists.
            cls = HttpCheckClass.OK_OWNED
        else:
            cls = HttpCheckClass.DEAD
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
