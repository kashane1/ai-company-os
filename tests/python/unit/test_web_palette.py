"""Tests for the palette intelligence module (design-intelligence work).

Stdlib-only, offline. Covers the WCAG contrast primitives, the curated genre
table's integrity, and the deterministic HSL synthesizer's AA guarantees.
"""

from __future__ import annotations

import math

import pytest

from packages.web.palette import (
    AA_NORMAL,
    GENRE_PALETTES,
    Palette,
    Unresolvable,
    best_text_on,
    contrast_ratio,
    derive_palette,
    palette_for_genre,
    parse_color,
    passes_aa,
    relative_luminance,
)


# --- parse_color -----------------------------------------------------------

@pytest.mark.parametrize(
    "value,expected",
    [
        ("#fff", (255, 255, 255)),
        ("#000000", (0, 0, 0)),
        ("#1E293B", (30, 41, 59)),
        ("#ffffffff", (255, 255, 255)),  # opaque 8-digit
        ("rgb(255, 0, 0)", (255, 0, 0)),
        ("rgb(255 0 0)", (255, 0, 0)),  # modern space form
        ("rgba(0,0,0,1)", (0, 0, 0)),
        ("rgb(100% 0% 0%)", (255, 0, 0)),
        ("hsl(0, 100%, 50%)", (255, 0, 0)),
        ("hsl(120 100% 50%)", (0, 255, 0)),
    ],
)
def test_parse_color_opaque(value, expected):
    assert parse_color(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "var(--brand)",
        "color-mix(in srgb, #fff 50%, #000)",
        "light-dark(#fff, #000)",
        "currentColor",
        "#ffffff80",  # translucent
        "rgba(0,0,0,0.5)",
        "hsla(0,100%,50%,0.2)",
        "not-a-color",
        "",
    ],
)
def test_parse_color_unresolvable(value):
    with pytest.raises(Unresolvable):
        parse_color(value)


# --- contrast math (anchored to WCAG worked examples) ----------------------

def test_black_white_is_21_to_1():
    assert math.isclose(contrast_ratio("#000000", "#ffffff"), 21.0, rel_tol=1e-3)


def test_identical_colors_is_1_to_1():
    assert math.isclose(contrast_ratio("#abcdef", "#abcdef"), 1.0, rel_tol=1e-9)


def test_ratio_is_symmetric():
    assert contrast_ratio("#123456", "#fedcba") == contrast_ratio("#fedcba", "#123456")


def test_relative_luminance_endpoints():
    assert math.isclose(relative_luminance("#000000"), 0.0, abs_tol=1e-9)
    assert math.isclose(relative_luminance("#ffffff"), 1.0, abs_tol=1e-9)


def test_passes_aa_thresholds():
    assert passes_aa("#595959", "#ffffff")  # ~7:1, passes normal
    assert not passes_aa("#999999", "#ffffff")  # ~2.85:1, fails normal
    assert passes_aa("#949494", "#ffffff", large=True)  # large bar is lower


def test_best_text_on_picks_higher_contrast():
    assert best_text_on("#000000") == "#ffffff"
    assert best_text_on("#ffffff") == "#111111"
    # And the choice actually wins:
    bg = "#1E293B"
    assert contrast_ratio(best_text_on(bg), bg) >= contrast_ratio(
        "#ffffff" if best_text_on(bg) == "#111111" else "#111111", bg
    )


# --- curated genre table integrity -----------------------------------------

def test_genre_table_covers_the_twenty_genres():
    assert len(GENRE_PALETTES) == 20


@pytest.mark.parametrize("genre,pal", list(GENRE_PALETTES.items()))
def test_curated_palettes_are_legible(genre, pal):
    # Body text on the light background is the strict bar: normal text, 4.5:1.
    assert passes_aa(pal.fg, pal.bg), f"{genre}: fg/bg below 4.5:1"
    # On-color labels (CTA text on accent, text on the brand surface) sit on
    # buttons/headers — large/bold text and UI components, so the WCAG bar is
    # 3:1 (§1.4.3 large / §1.4.11). The source data is tuned to exactly this.
    assert passes_aa(pal.on_accent, pal.accent, large=True), f"{genre}: accent/on_accent below 3:1"
    assert passes_aa(pal.on_primary, pal.primary, large=True), f"{genre}: primary/on_primary below 3:1"


@pytest.mark.parametrize("genre,pal", list(GENRE_PALETTES.items()))
def test_curated_palette_values_parse(genre, pal):
    for field in (pal.primary, pal.secondary, pal.accent, pal.bg, pal.fg, pal.border):
        parse_color(field)  # raises if malformed


def test_palette_for_genre_lookup():
    assert palette_for_genre("plumber") is GENRE_PALETTES["plumber"]
    assert palette_for_genre("nonexistent_genre") is None


def test_as_css_vars_shape():
    vars_ = GENRE_PALETTES["bakery"].as_css_vars()
    assert set(vars_) == {"--brand", "--brand-contrast", "--secondary", "--accent", "--on-accent"}


# --- derive_palette synthesizer --------------------------------------------

@pytest.mark.parametrize("brand", ["#2563EB", "#DC2626", "#15803D", "#7C3AED", "#0F172A", "#F59E0B"])
@pytest.mark.parametrize("mood", ["auto", "calm", "friendly", "bold"])
def test_derived_accent_always_passes_aa(brand, mood):
    pal = derive_palette(brand, mood=mood)
    # The synthesizer's contract: CTA text on accent is always AA-legible.
    assert contrast_ratio(pal.on_accent, pal.accent) >= AA_NORMAL


def test_derive_is_deterministic():
    a = derive_palette("#2563EB", mood="auto")
    b = derive_palette("#2563EB", mood="auto")
    assert a == b


def test_derive_returns_palette_with_parseable_colors():
    pal = derive_palette("#2563EB")
    assert isinstance(pal, Palette)
    for field in (pal.primary, pal.secondary, pal.accent, pal.on_accent):
        parse_color(field)


def test_derived_accent_differs_from_brand():
    pal = derive_palette("#2563EB", mood="auto")
    assert pal.accent.lower() != pal.primary.lower()
