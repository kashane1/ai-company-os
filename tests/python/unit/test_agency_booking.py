"""Tests for booking embed injection (G6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.booking import (
    BookingError,
    BookingSetup,
    inject_booking_embed,
    inject_booking_html_into_file,
    inject_booking_into_file,
    load_booking_setup,
    render_booking_embed,
    save_booking_setup,
)

CAL_URL = "https://calendly.com/joes-plumbing"


def test_render_known_provider() -> None:
    embed = render_booking_embed("calendly", CAL_URL)
    assert CAL_URL in embed
    assert "calendly.com/assets/external/widget.js" in embed


def test_unsupported_provider_rejected() -> None:
    with pytest.raises(BookingError, match="unsupported provider"):
        render_booking_embed("mybooker", CAL_URL)


@pytest.mark.parametrize("bad", ["javascript:alert(1)", "ftp://x", 'https://x" onload="y'])
def test_bad_url_rejected(bad: str) -> None:
    with pytest.raises(BookingError):
        render_booking_embed("calendly", bad)


def test_inject_before_body() -> None:
    html = "<html><body><h1>Joe's</h1></body></html>"
    out = inject_booking_embed(html, render_booking_embed("acuity", CAL_URL))
    assert "bbw:booking:start" in out
    assert out.count("</body>") == 1
    assert "calendly.com/joes-plumbing" in out


def test_inject_is_idempotent() -> None:
    html = "<html><body><h1>Joe's</h1></body></html>"
    embed = render_booking_embed("calendly", CAL_URL)
    once = inject_booking_embed(html, embed)
    twice = inject_booking_embed(once, embed)
    assert once == twice  # re-run replaces, never appends
    assert twice.count("bbw:booking:start") == 1


def test_inject_uses_marker_when_present() -> None:
    html = "<html><body><!-- BOOKING_EMBED --></body></html>"
    out = inject_booking_embed(html, render_booking_embed("square", CAL_URL))
    assert "<!-- BOOKING_EMBED -->" not in out
    assert "bbw:booking:start" in out


def test_no_target_raises() -> None:
    with pytest.raises(BookingError, match="no injection target"):
        inject_booking_embed("<div>fragment</div>", "x")


def test_inject_file_and_record(tmp_path: Path) -> None:
    site = tmp_path / "index.html"
    site.write_text("<html><body>hi</body></html>", encoding="utf-8")
    inject_booking_into_file(site, "calendly", CAL_URL)
    assert "bbw:booking:start" in site.read_text(encoding="utf-8")

    record = BookingSetup(
        product_id="joes-plumbing-site", provider="calendly", booking_url=CAL_URL,
        injected=True, completed_at="2026-06-04T00:00:00Z",
    )
    save_booking_setup(record, root=tmp_path / "svc")
    assert load_booking_setup("joes-plumbing-site", root=tmp_path / "svc") == record


def test_calendly_embed_auto_resizes() -> None:
    embed = render_booking_embed("calendly", CAL_URL)
    assert 'data-resize="true"' in embed


def test_acuity_embed_includes_resize_script() -> None:
    embed = render_booking_embed("acuity", CAL_URL)
    assert "embed.acuityscheduling.com/js/embed.js" in embed
    assert CAL_URL in embed


def test_inject_raw_html_snippet_idempotent(tmp_path: Path) -> None:
    site = tmp_path / "index.html"
    site.write_text("<html><body>hi</body></html>", encoding="utf-8")
    # Square's advanced widget is account-specific HTML pasted from the dashboard.
    snippet = '<div class="sq-booking">book</div>'
    inject_booking_html_into_file(site, snippet)
    inject_booking_html_into_file(site, snippet)  # re-run replaces, never appends
    text = site.read_text(encoding="utf-8")
    assert text.count("bbw:booking:start") == 1
    assert "sq-booking" in text


def test_inject_empty_raw_html_rejected(tmp_path: Path) -> None:
    site = tmp_path / "index.html"
    site.write_text("<html><body>hi</body></html>", encoding="utf-8")
    with pytest.raises(BookingError, match="empty booking embed"):
        inject_booking_html_into_file(site, "   ")


def test_booking_setup_managed_roundtrip(tmp_path: Path) -> None:
    record = BookingSetup(
        product_id="acme-site", provider="acuity", booking_url=CAL_URL, managed=True,
    )
    save_booking_setup(record, root=tmp_path / "svc")
    loaded = load_booking_setup("acme-site", root=tmp_path / "svc")
    assert loaded is not None and loaded.managed is True


def test_booking_setup_legacy_dict_defaults_unmanaged() -> None:
    # A record persisted before `managed` existed must still load (defaults False).
    legacy = {"product_id": "x", "provider": "calendly", "booking_url": CAL_URL}
    assert BookingSetup.from_dict(legacy).managed is False
