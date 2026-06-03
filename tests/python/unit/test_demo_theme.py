"""Tests for deterministic offline demo theming (Agency layer).

Pure, no network: every theme is derived from ``genre_id`` + ``place_id`` only.
"""

from __future__ import annotations

import re

import pytest

from packages.agency.demo_theme import (
    LAYOUTS,
    STYLE_PROFILES,
    DemoTheme,
    _contrast_for,
    _hsl_to_rgb,
    _relative_luminance,
    apply_theme,
    theme_for_record,
    theme_style_block,
)

RECORD = {
    "place_id": "ChIJtest123",
    "display_name": "Joe's Plumbing",
    "genre_id": "plumber",
}

_HEX_RE = re.compile(r"^#[0-9a-f]{6}$")


def test_theme_is_deterministic() -> None:
    a = theme_for_record(RECORD)
    b = theme_for_record(dict(RECORD))
    assert a == b


def test_same_genre_different_business_differs() -> None:
    # Two plumbers should not get an identical look.
    a = theme_for_record({**RECORD, "place_id": "ChIJ-aaaaaa"})
    b = theme_for_record({**RECORD, "place_id": "ChIJ-zzzzzz"})
    assert (a.brand, a.layout, a.heading_font) != (b.brand, b.layout, b.heading_font) or a.brand != b.brand


def test_layout_is_valid_and_genre_eligible() -> None:
    for genre, profile in STYLE_PROFILES.items():
        theme = theme_for_record({"place_id": f"seed-{genre}", "genre_id": genre})
        assert theme.layout in LAYOUTS
        assert theme.layout in profile.layouts
        assert theme.style_class == profile.style_class


def test_unknown_genre_falls_back() -> None:
    theme = theme_for_record({"place_id": "x", "genre_id": "does_not_exist"})
    assert theme.style_class == "default"
    assert theme.layout in LAYOUTS


def test_every_known_genre_maps() -> None:
    # Every genre we actually build demos for must have a profile.
    expected = {
        "auto_repair", "barber_shop", "bakery", "dog_groomer", "plumber",
        "nail_salon", "electrician", "notary", "beauty_salon", "accountant",
        "massage_therapy", "garage_door", "coffee_shop", "roofer", "landscaper",
        "tutoring", "music_lessons", "house_cleaning", "restaurant", "yoga_studio",
    }
    assert expected <= set(STYLE_PROFILES)


def test_brand_colors_are_valid_hex() -> None:
    theme = theme_for_record(RECORD)
    assert _HEX_RE.match(theme.brand)
    assert _HEX_RE.match(theme.brand_strong)
    assert theme.brand_contrast in ("#ffffff", "#15172b")


def test_contrast_picks_readable_foreground() -> None:
    assert _contrast_for((0, 0, 0)) == "#ffffff"  # white on black
    assert _contrast_for((255, 255, 255)) == "#15172b"  # dark on white


def test_hsl_to_rgb_known_values() -> None:
    assert _hsl_to_rgb(0, 1.0, 0.5) == (255, 0, 0)
    assert _hsl_to_rgb(120, 1.0, 0.5) == (0, 255, 0)
    assert _hsl_to_rgb(240, 1.0, 0.5) == (0, 0, 255)
    assert _hsl_to_rgb(0, 0.0, 1.0) == (255, 255, 255)


def test_luminance_monotonic() -> None:
    assert _relative_luminance((0, 0, 0)) < _relative_luminance((128, 128, 128))
    assert _relative_luminance((128, 128, 128)) < _relative_luminance((255, 255, 255))


def test_font_import_url_well_formed() -> None:
    theme = theme_for_record(RECORD)
    assert theme.font_import_url.startswith("https://fonts.googleapis.com/css2?")
    assert "display=swap" in theme.font_import_url
    assert " " not in theme.font_import_url  # spaces encoded as '+'


def test_style_block_overrides_brand_and_fonts() -> None:
    theme = theme_for_record(RECORD)
    block = theme_style_block(theme)
    assert f"--brand:{theme.brand};" in block
    assert "--font-heading:" in block
    assert f'body[data-layout="{theme.layout}"]' in block


def test_apply_theme_injects_into_head_and_body() -> None:
    theme = theme_for_record(RECORD)
    html = "<html><head><title>x</title></head><body>\n<main></main></body></html>"
    out = apply_theme(html, theme)
    assert out.count("</head>") == 1
    assert "<style>" in out.split("</head>")[0]  # block is before </head>
    assert f'<body data-layout="{theme.layout}"' in out
    assert f'data-theme="{theme.style_class}"' in out


def test_render_preview_html_is_themed_by_default() -> None:
    from packages.agency.prospect_site import render_preview_html

    record = {
        **RECORD,
        "city_id": "oklahoma_city",
        "formatted_address": "100 Main St, Oklahoma City, OK 73119, USA",
        "phone": "+1 405-555-0100",
    }
    html = render_preview_html(record)
    theme = theme_for_record(record)
    assert f'data-layout="{theme.layout}"' in html
    assert "fonts.googleapis.com" in html
    # Themed render must still leave no unfilled template tokens.
    assert "{{" not in html

    plain = render_preview_html(record, themed=False)
    assert "data-layout=" not in plain


def test_to_dict_is_serializable() -> None:
    theme = theme_for_record(RECORD)
    d = theme.to_dict()
    assert d["layout"] == theme.layout
    assert d["style_class"] == theme.style_class
    assert set(d) >= {"style_class", "layout", "brand", "heading_font", "body_font"}
