"""Offline tests for packages/agency/demo_maps.py (no network)."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from packages.agency import demo_maps


@pytest.fixture
def _with_key(monkeypatch):
    monkeypatch.setattr(demo_maps, "get_api_key", lambda _name: "TEST_KEY_123")
    return "TEST_KEY_123"


@pytest.fixture
def _no_key(monkeypatch):
    monkeypatch.setattr(demo_maps, "get_api_key", lambda _name: None)


def test_has_key_reflects_resolver(_with_key):
    assert demo_maps.has_demo_maps_key() is True
    assert demo_maps.demo_maps_key() == "TEST_KEY_123"


def test_has_key_false_when_unset(_no_key):
    assert demo_maps.has_demo_maps_key() is False
    assert demo_maps.demo_maps_key() is None


def test_embed_place_url_encodes_query_and_key(_with_key):
    url = demo_maps.embed_place_url("Joe's Plumbing, Dallas, TX")
    parsed = urlparse(url)
    assert parsed.netloc == "www.google.com"
    assert parsed.path == "/maps/embed/v1/place"
    params = parse_qs(parsed.query)
    assert params["key"] == ["TEST_KEY_123"]
    assert params["q"] == ["Joe's Plumbing, Dallas, TX"]


def test_static_map_url_has_marker_and_zoom(_with_key):
    url = demo_maps.static_map_url("123 Main St, Dallas, TX", zoom=12, size="400x200")
    params = parse_qs(urlparse(url).query)
    assert params["center"] == ["123 Main St, Dallas, TX"]
    assert params["zoom"] == ["12"]
    assert params["size"] == ["400x200"]
    assert params["markers"][0].startswith("color:red|")


def test_url_builders_use_explicit_key_override(_no_key):
    # Even with no configured key, an explicit key is honored.
    url = demo_maps.embed_place_url("Somewhere", key="OVERRIDE")
    assert "key=OVERRIDE" in url


def test_url_builders_raise_without_any_key(_no_key):
    with pytest.raises(demo_maps.DemoMapsKeyError):
        demo_maps.embed_place_url("Somewhere")
    with pytest.raises(demo_maps.DemoMapsKeyError):
        demo_maps.static_map_url("Somewhere")


def test_empty_query_rejected(_with_key):
    with pytest.raises(ValueError):
        demo_maps.embed_place_url("   ")
    with pytest.raises(ValueError):
        demo_maps.static_map_url("")


def test_iframe_html_renders_when_key_present(_with_key):
    markup = demo_maps.embed_iframe_html("Joe's Plumbing, Dallas, TX")
    assert markup.startswith("<iframe")
    assert "maps/embed/v1/place" in markup
    assert "loading=\"lazy\"" in markup
    # Query is URL-encoded inside the src, and the param '&' is HTML-escaped.
    assert "q=Joe%27s+Plumbing" in markup
    assert "&amp;q=" in markup


def test_iframe_html_escapes_title(_with_key):
    markup = demo_maps.embed_iframe_html("X", title='Find "us" <here>')
    assert "<here>" not in markup
    assert "&lt;here&gt;" in markup


def test_iframe_html_empty_when_no_key(_no_key):
    assert demo_maps.embed_iframe_html("Joe's Plumbing") == ""
