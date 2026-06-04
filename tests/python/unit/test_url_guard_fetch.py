"""Tests for the guarded fetch helper (G2 [+G2-FETCH] / [X-PORT])."""

from __future__ import annotations

import pytest

from packages.policies.url_guard import (
    FetchResponse,
    UnsafeUrlError,
    fetch_public_url,
)

PUBLIC = lambda host: ["93.184.216.34"]  # noqa: E731
INTERNAL = lambda host: ["169.254.169.254"]  # noqa: E731


def _opener(responses):
    """Return a fake opener yielding queued FetchResponses by call order."""
    calls = iter(responses)

    def opener(url, timeout, max_bytes):
        return next(calls)

    return opener


def test_happy_path_returns_capped_text() -> None:
    opener = _opener([FetchResponse(200, {}, b"<html>hello</html>")])
    page = fetch_public_url("https://example.com", resolver=PUBLIC, opener=opener)
    assert page.status == 200
    assert page.final_url == "https://example.com"
    assert "hello" in page.text
    assert page.redirects == 0


def test_redirect_to_internal_is_reguarded_and_rejected() -> None:
    # First hop (public) 302s to an internal host; the per-hop re-guard must reject.
    def resolver(host):
        return ["93.184.216.34"] if host == "example.com" else ["169.254.169.254"]

    opener = _opener([FetchResponse(302, {"location": "http://169.254.169.254/"}, b"")])
    with pytest.raises(UnsafeUrlError):
        fetch_public_url("https://example.com", resolver=resolver, opener=opener)


def test_non_standard_port_is_rejected() -> None:
    opener = _opener([FetchResponse(200, {}, b"x")])
    with pytest.raises(UnsafeUrlError, match="port 5432"):
        fetch_public_url("http://example.com:5432/", resolver=PUBLIC, opener=opener)


def test_body_is_capped() -> None:
    opener = _opener([FetchResponse(200, {}, b"A" * 5000)])
    page = fetch_public_url("https://example.com", resolver=PUBLIC, opener=opener, max_bytes=100)
    assert page.bytes_read == 100


def test_too_many_redirects() -> None:
    loop = [FetchResponse(302, {"location": "https://example.com/next"}, b"")] * 10
    opener = _opener(loop)
    with pytest.raises(UnsafeUrlError, match="too many redirects"):
        fetch_public_url("https://example.com", resolver=PUBLIC, opener=opener, max_redirects=3)


def test_initial_internal_target_rejected_before_fetch() -> None:
    opener = _opener([FetchResponse(200, {}, b"should-not-be-read")])
    with pytest.raises(UnsafeUrlError):
        fetch_public_url(
            "http://169.254.169.254/latest/meta-data/", resolver=INTERNAL, opener=opener
        )
