"""Tests for online-ordering embed injection + platform gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.ordering import (
    OrderingError,
    OrderingSetup,
    assert_modifiers_supported,
    assert_platform_supported,
    check_modifiers,
    check_platform_for_tier,
    inject_order_embed,
    inject_order_html_into_file,
    inject_order_into_file,
    load_ordering_setup,
    recommend_platform,
    render_order_embed,
    save_ordering_setup,
)

ORDER_URL = "https://order.square.site/joes-coffee"


def test_render_known_platform() -> None:
    embed = render_order_embed("square", ORDER_URL)
    assert ORDER_URL in embed
    assert 'class="order-online"' in embed
    assert "Order Online" in embed


def test_render_custom_label() -> None:
    embed = render_order_embed("clover", ORDER_URL, label="Order Pickup")
    assert "Order Pickup" in embed
    assert "Order Online" not in embed


def test_unsupported_platform_rejected() -> None:
    with pytest.raises(OrderingError, match="unsupported platform"):
        render_order_embed("doordash", ORDER_URL)


@pytest.mark.parametrize("bad", ["javascript:alert(1)", "ftp://x", 'https://x" onload="y'])
def test_bad_url_rejected(bad: str) -> None:
    with pytest.raises(OrderingError):
        render_order_embed("square", bad)


def test_inject_before_body() -> None:
    html = "<html><body><h1>Joe's</h1></body></html>"
    out = inject_order_embed(html, render_order_embed("square", ORDER_URL))
    assert "bbw:ordering:start" in out
    assert out.count("</body>") == 1
    assert "order.square.site/joes-coffee" in out


def test_inject_is_idempotent() -> None:
    html = "<html><body><h1>Joe's</h1></body></html>"
    embed = render_order_embed("square", ORDER_URL)
    once = inject_order_embed(html, embed)
    twice = inject_order_embed(once, embed)
    assert once == twice  # re-run replaces, never appends
    assert twice.count("bbw:ordering:start") == 1


def test_inject_uses_marker_when_present() -> None:
    html = "<html><body><!-- ORDER_ONLINE_EMBED --></body></html>"
    out = inject_order_embed(html, render_order_embed("clover", ORDER_URL))
    assert "<!-- ORDER_ONLINE_EMBED -->" not in out
    assert "bbw:ordering:start" in out


def test_no_target_raises() -> None:
    with pytest.raises(OrderingError, match="no injection target"):
        inject_order_embed("<div>fragment</div>", "x")


def test_inject_file_and_record(tmp_path: Path) -> None:
    site = tmp_path / "index.html"
    site.write_text("<html><body>hi</body></html>", encoding="utf-8")
    inject_order_into_file(site, "square", ORDER_URL)
    assert "bbw:ordering:start" in site.read_text(encoding="utf-8")

    record = OrderingSetup(
        product_id="joes-coffee-site", platform="square", ordering_url=ORDER_URL,
        base="ordering_setup", injected=True, completed_at="2026-06-15T00:00:00Z",
    )
    save_ordering_setup(record, root=tmp_path / "svc")
    assert load_ordering_setup("joes-coffee-site", root=tmp_path / "svc") == record


def test_inject_raw_html_snippet_idempotent(tmp_path: Path) -> None:
    site = tmp_path / "index.html"
    site.write_text("<html><body>hi</body></html>", encoding="utf-8")
    # Square Online's order button is account-specific HTML pasted from the dashboard.
    snippet = '<div class="sq-online-ordering">order</div>'
    inject_order_html_into_file(site, snippet)
    inject_order_html_into_file(site, snippet)  # re-run replaces, never appends
    text = site.read_text(encoding="utf-8")
    assert text.count("bbw:ordering:start") == 1
    assert "sq-online-ordering" in text


def test_inject_empty_raw_html_rejected(tmp_path: Path) -> None:
    site = tmp_path / "index.html"
    site.write_text("<html><body>hi</body></html>", encoding="utf-8")
    with pytest.raises(OrderingError, match="empty ordering embed"):
        inject_order_html_into_file(site, "   ")


# --- platform / tier gate ---------------------------------------------------

def test_setup_on_toast_is_a_hard_block() -> None:
    errors, _ = check_platform_for_tier("toast", "ordering_setup")
    assert errors and "not supported" in errors[0]
    with pytest.raises(OrderingError, match="ordering_setup"):
        assert_platform_supported("toast", "ordering_setup")


def test_connect_on_toast_is_a_warning_not_a_block() -> None:
    errors, warnings = check_platform_for_tier("toast", "ordering_connect")
    assert errors == []
    assert warnings and "ordering_connect" in warnings[0]
    # No raise — Connect against an existing Toast link is deliverable (gated).
    assert_platform_supported("toast", "ordering_connect")


def test_square_and_clover_fully_supported_for_both_tiers() -> None:
    for platform in ("square", "clover"):
        for base in ("ordering_connect", "ordering_setup"):
            assert check_platform_for_tier(platform, base) == ([], [])


def test_unknown_base_is_an_error() -> None:
    errors, _ = check_platform_for_tier("square", "ordering_teleport")
    assert errors and "unknown ordering base" in errors[0]


def test_unknown_platform_in_tier_check_is_an_error() -> None:
    errors, _ = check_platform_for_tier("grubhub", "ordering_connect")
    assert errors and "unsupported platform" in errors[0]


# --- modifiers --------------------------------------------------------------

def test_unknown_modifier_is_an_error() -> None:
    assert check_modifiers(["ordering_teleport"]) == [
        "unknown ordering modifier 'ordering_teleport'"
    ]
    with pytest.raises(OrderingError, match="unknown ordering modifier"):
        assert_modifiers_supported(["ordering_teleport"])


def test_known_modifiers_pass() -> None:
    assert check_modifiers(["ordering_menu_entry", "ordering_management"]) == []


# --- recommend_platform -----------------------------------------------------

def test_recommend_platform_defaults_to_square() -> None:
    assert recommend_platform() == "square"
    assert recommend_platform("") == "square"
    assert recommend_platform("shopify") == "square"


def test_recommend_platform_keeps_existing_clover_or_toast() -> None:
    assert recommend_platform("clover") == "clover"
    assert recommend_platform("Toast") == "toast"


# --- record validation / roundtrip ------------------------------------------

def test_setup_validate_blocks_toast_setup(tmp_path: Path) -> None:
    record = OrderingSetup(
        product_id="acme-site", platform="toast", ordering_url=ORDER_URL,
        base="ordering_setup",
    )
    with pytest.raises(OrderingError, match="ordering_setup"):
        save_ordering_setup(record, root=tmp_path / "svc")


def test_setup_managed_and_modifiers_roundtrip(tmp_path: Path) -> None:
    record = OrderingSetup(
        product_id="acme-site", platform="clover", ordering_url=ORDER_URL,
        base="ordering_setup", managed=True,
        modifiers=("ordering_menu_entry", "ordering_management"),
    )
    save_ordering_setup(record, root=tmp_path / "svc")
    loaded = load_ordering_setup("acme-site", root=tmp_path / "svc")
    assert loaded is not None
    assert loaded.managed is True
    assert loaded.modifiers == record.modifiers


def test_setup_legacy_dict_defaults(tmp_path: Path) -> None:
    # A record persisted before `base`/`managed` existed must still load.
    legacy = {"product_id": "x", "platform": "square", "ordering_url": ORDER_URL}
    rec = OrderingSetup.from_dict(legacy)
    assert rec.base == "ordering_connect"
    assert rec.managed is False
