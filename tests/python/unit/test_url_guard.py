"""SSRF guard tests — no real network (resolver is injected)."""

from __future__ import annotations

import pytest

from packages.policies.url_guard import (
    UnsafeUrlError,
    assert_safe_public_url,
    is_safe_public_url,
)

PUBLIC = lambda host: ["93.184.216.34"]  # noqa: E731
PRIVATE = lambda host: ["10.0.0.5"]  # noqa: E731
METADATA = lambda host: ["169.254.169.254"]  # noqa: E731
UNRESOLVABLE = lambda host: []  # noqa: E731


def test_allows_public_http_and_https() -> None:
    assert is_safe_public_url("https://example.com", resolver=PUBLIC)
    assert is_safe_public_url("http://example.com/path?q=1#x", resolver=PUBLIC)


def test_blocks_non_http_schemes() -> None:
    for url in ("ftp://example.com", "file:///etc/passwd", "gopher://x", "javascript:alert(1)"):
        assert not is_safe_public_url(url, resolver=PUBLIC), url


def test_blocks_literal_private_loopback_and_metadata() -> None:
    for url in (
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://192.168.1.10/",
        "http://172.16.5.4/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://0.0.0.0/",
    ):
        assert not is_safe_public_url(url, resolver=PUBLIC), url


def test_blocks_hostnames_resolving_to_private_or_metadata() -> None:
    assert not is_safe_public_url("http://intranet.corp", resolver=PRIVATE)
    assert not is_safe_public_url("http://metadata.google", resolver=METADATA)


def test_blocks_unresolvable_and_credentialed_and_empty() -> None:
    assert not is_safe_public_url("http://nope.invalid", resolver=UNRESOLVABLE)
    assert not is_safe_public_url("http://user:pass@example.com", resolver=PUBLIC)
    assert not is_safe_public_url("", resolver=PUBLIC)


def test_assert_raises_unsafe() -> None:
    with pytest.raises(UnsafeUrlError):
        assert_safe_public_url("http://169.254.169.254/", resolver=PUBLIC)
    assert_safe_public_url("https://example.com", resolver=PUBLIC)  # does not raise
