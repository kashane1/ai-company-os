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
