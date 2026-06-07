"""Tests for booking embed injection (G6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.booking import (
    BookingError,
    BookingSetup,
    assert_modifiers_supported,
    check_modifiers_for_platform,
    inject_booking_embed,
    inject_booking_html_into_file,
    inject_booking_into_file,
    load_booking_setup,
    recommend_platform,
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


def test_classes_not_supported_on_calendly_is_a_hard_block() -> None:
    errors, _ = check_modifiers_for_platform("calendly", ["booking_classes"])
    assert errors and "not supported" in errors[0]
    with pytest.raises(BookingError, match="booking_classes"):
        assert_modifiers_supported("calendly", ["booking_classes"])


def test_classes_supported_on_square_and_acuity() -> None:
    for provider in ("square", "acuity", "vagaro", "booksy"):
        errors, _ = check_modifiers_for_platform(provider, ["booking_classes"])
        assert errors == []


def test_partial_deposit_is_a_warning_not_a_block() -> None:
    # Deliverable (full prepay) but degraded — advisory, not an error.
    errors, warnings = check_modifiers_for_platform("square", ["booking_deposits"])
    assert errors == []
    assert warnings and "booking_deposits" in warnings[0]
    # Acuity does true % deposits — no warning.
    assert check_modifiers_for_platform("acuity", ["booking_deposits"]) == ([], [])


def test_unknown_modifier_is_an_error() -> None:
    errors, _ = check_modifiers_for_platform("acuity", ["booking_teleport"])
    assert errors and "unknown booking modifier" in errors[0]


def test_booking_setup_validate_blocks_impossible_modifier(tmp_path: Path) -> None:
    record = BookingSetup(
        product_id="acme-site",
        provider="calendly",
        booking_url=CAL_URL,
        modifiers=("booking_classes",),
    )
    with pytest.raises(BookingError, match="booking_classes"):
        save_booking_setup(record, root=tmp_path / "svc")


def test_booking_setup_modifiers_roundtrip(tmp_path: Path) -> None:
    record = BookingSetup(
        product_id="acme-site",
        provider="acuity",
        booking_url=CAL_URL,
        modifiers=("booking_deposits", "booking_classes", "booking_intake"),
    )
    save_booking_setup(record, root=tmp_path / "svc")
    loaded = load_booking_setup("acme-site", root=tmp_path / "svc")
    assert loaded is not None and loaded.modifiers == record.modifiers


def test_recommend_platform_routes_advanced_needs_to_acuity() -> None:
    assert recommend_platform(["booking_classes"]) == "acuity"
    assert recommend_platform(["booking_deposits", "booking_intake"]) == "acuity"
    assert recommend_platform(["booking_management"]) == "calendly"
    assert recommend_platform([]) == "calendly"


def test_booking_setup_legacy_dict_defaults_unmanaged() -> None:
    # A record persisted before `managed` existed must still load (defaults False).
    legacy = {"product_id": "x", "provider": "calendly", "booking_url": CAL_URL}
    assert BookingSetup.from_dict(legacy).managed is False
