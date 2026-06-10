from __future__ import annotations

from datetime import datetime, timezone

import httpx

from packages.prospecting.http_check import HTTPChecker, should_check_http
from packages.schemas.prospect import HttpCheckClass, MapsWebsiteClass, ProspectRecord


def _record(place_id: str, maps_class: MapsWebsiteClass, url: str = "") -> ProspectRecord:
    return ProspectRecord(
        place_id=place_id,
        display_name="Local Business",
        formatted_address="Seattle, WA",
        phone="",
        types=[],
        city_id="seattle",
        genre_id="auto_repair",
        grid_cell_id="seattle:auto_repair",
        maps_website_uri=url,
        maps_website_class=maps_class,
    )


def test_http_queue_rules_check_missing_or_rented_presence_and_sample_owned() -> None:
    assert should_check_http(_record("places/no-site", MapsWebsiteClass.ABSENT)) is True
    assert should_check_http(_record("places/social", MapsWebsiteClass.SOCIAL_ONLY, "https://facebook.com/x")) is True
    assert should_check_http(_record("places/market", MapsWebsiteClass.MARKETPLACE, "https://yelp.com/biz/x")) is True

    present_checked = [
        should_check_http(_record(f"places/{i}", MapsWebsiteClass.PRESENT, "https://example.com"))
        for i in range(100)
    ]
    assert 1 <= sum(present_checked) <= 10


def test_http_checker_classifies_dead_parked_and_social_redirects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "dead.example":
            return httpx.Response(404)
        if request.url.host == "parked.example":
            return httpx.Response(200, text="This domain is for sale at Sedo")
        return httpx.Response(200, headers={"location": "https://facebook.com/local"})

    checker = HTTPChecker(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        now=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        enforce_public_url=False,  # reserved .example hosts don't resolve
    )

    assert checker.check("https://dead.example").http_check_class is HttpCheckClass.DEAD
    assert checker.check("https://parked.example").http_check_class is HttpCheckClass.PARKED
    assert (
        checker.check("https://facebook.com/local").http_check_class
        is HttpCheckClass.REDIRECT_SOCIAL
    )


def test_http_checker_retries_transient_timeout_before_classifying() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.TimeoutException("transient timeout")
        return httpx.Response(200, text="owned site", request=request)

    checker = HTTPChecker(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        now=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        enforce_public_url=False,
    )

    check = checker.check("https://owned.example")

    assert attempts == 2
    assert check.http_check_class is HttpCheckClass.OK_OWNED


def test_http_checker_treats_waf_blocked_status_as_live_owned_site() -> None:
    # A 403/503 from a WAF means the server is up and the site exists — it must
    # NOT be classified as dead (the cohort-B false-positive bug).
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "cloudflared.example":
            return httpx.Response(403, text="Access denied / Cloudflare")
        return httpx.Response(451, text="unavailable for legal reasons")

    checker = HTTPChecker(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        now=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        enforce_public_url=False,
    )

    assert checker.check("https://cloudflared.example").http_check_class is HttpCheckClass.OK_OWNED
    assert checker.check("https://legalblock.example").http_check_class is HttpCheckClass.OK_OWNED


def test_http_checker_genuinely_gone_and_broken_stay_dead() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "gone.example":
            return httpx.Response(410)
        return httpx.Response(500, text="internal error")  # 500 not an access gate

    checker = HTTPChecker(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        now=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        enforce_public_url=False,
        max_attempts=2,
    )

    assert checker.check("https://gone.example").http_check_class is HttpCheckClass.DEAD
    assert checker.check("https://broken.example").http_check_class is HttpCheckClass.DEAD


def test_http_checker_retries_transient_status_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, text="temporarily unavailable")
        return httpx.Response(200, text="owned site", request=request)

    checker = HTTPChecker(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        now=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        enforce_public_url=False,
    )

    check = checker.check("https://owned.example")
    assert attempts == 2
    assert check.http_check_class is HttpCheckClass.OK_OWNED


def test_http_checker_sends_browser_user_agent() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, text="owned site")

    checker = HTTPChecker(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        now=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
        enforce_public_url=False,
    )
    checker.check("https://owned.example")
    assert "Mozilla/5.0" in seen["ua"]
    assert "prospecting/1.0" not in seen["ua"]


def test_http_checker_blocks_non_public_url_ssrf() -> None:
    # The guard must reject a metadata/loopback target before any fetch happens.
    fetched = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal fetched
        fetched = True
        return httpx.Response(200, text="should not be reached")

    checker = HTTPChecker(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        now=lambda: datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    result = checker.check("http://169.254.169.254/latest/meta-data/")
    assert result.http_check_class is HttpCheckClass.ERROR
    assert "non-public" in (result.error or "")
    assert fetched is False  # never hit the network
