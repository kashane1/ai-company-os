"""Tests for the mood-board generator (palette + type + 6–9 images on one page).

Locks the pure core: vibe→font resolution, the business-first image merge, and a
self-contained render that never leaks a ``{{TOKEN}}``. A recipe-only kit (no
exemplars) is a first-class case — boards render with 0–N images, so we assert the
``want`` cap + priority, not a hard 6-image floor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.web.art_direction import GenreKit, KitRecipe
from packages.web.imagery import (
    PROVENANCE_GENERATED,
    PROVENANCE_OWNER,
    ImageAsset,
    ImageryManifest,
)
from packages.web.moodboard import (
    DEFAULT_VIBE,
    FONT_VIBES,
    collect_images,
    fonts_for_vibe,
    moodboard_from_kit,
    render_moodboard_html,
)
from packages.web.palette import GENRE_PALETTES


def _kit(**over) -> GenreKit:
    recipe = KitRecipe(
        slug=over.pop("slug", "demo"),
        display_name=over.pop("display_name", "Demo Kit"),
        palette=over.pop("palette", "genre:coffee_shop"),
        type_vibe=over.pop("type_vibe", "warm"),
        concept_statement=over.pop("concept_statement", "the morning ritual"),
        composition_rules=over.pop("composition_rules", ["Hero: the room at golden hour."]),
        imagery_direction=over.pop("imagery_direction", "warm, lived-in"),
        **over,
    )
    return GenreKit(recipe=recipe, manifest=ImageryManifest(), dir=Path("/tmp/demo"))


def test_fonts_for_vibe_resolves_and_defaults() -> None:
    assert fonts_for_vibe("elegant").display == "Playfair Display"
    assert fonts_for_vibe("warm").display == "Fraunces"
    # Unknown vibe → the documented default, never a crash.
    assert fonts_for_vibe("nonsense") == FONT_VIBES[DEFAULT_VIBE]
    assert fonts_for_vibe("") == FONT_VIBES[DEFAULT_VIBE]


def test_collect_images_is_business_first_deduped_and_capped() -> None:
    business = ImageryManifest(
        assets=[
            ImageAsset(id="hero", role="hero", path="b/hero.png", provenance=PROVENANCE_OWNER),
            ImageAsset(id="dropped", role="supporting", path="b/x.png",
                       provenance=PROVENANCE_OWNER, selected=False),
        ]
    )
    kit = ImageryManifest(
        assets=[
            ImageAsset(id="hero", role="hero", path="k/hero.webp", provenance=PROVENANCE_GENERATED),
            ImageAsset(
                id="s1", role="supporting", path="k/s1.webp", provenance=PROVENANCE_GENERATED
            ),
            ImageAsset(
                id="s2", role="supporting", path="k/s2.webp", provenance=PROVENANCE_GENERATED
            ),
        ]
    )
    merged = collect_images(business, kit, want=9)
    # business 'hero' wins the dedupe; unselected dropped; kit fills the rest.
    assert [a.id for a in merged] == ["hero", "s1", "s2"]
    assert merged[0].path == "b/hero.png"
    # cap honored
    assert len(collect_images(business, kit, want=2)) == 2


def test_moodboard_from_kit_pulls_palette_type_and_notes() -> None:
    board = moodboard_from_kit(_kit(), business_name="Bean & Gather", images=["assets/a.webp"])
    assert board.business_name == "Bean & Gather"
    assert board.palette == GENRE_PALETTES["coffee_shop"]
    assert board.font.display == "Fraunces"  # warm vibe
    assert board.concept_statement == "the morning ritual"
    # composition_rules + imagery_direction become the direction notes.
    assert any("golden hour" in n for n in board.direction_notes)
    assert any("lived-in" in n for n in board.direction_notes)


def test_render_is_self_contained_with_swatches_and_images() -> None:
    board = moodboard_from_kit(
        _kit(), business_name="Bean & Gather", images=["assets/a.webp", "assets/b.webp"]
    )
    html = render_moodboard_html(board)
    assert html.startswith("<!doctype html>")
    assert html.count('class="sw"') == 4  # primary/secondary/accent/surface swatches
    assert html.count("<img ") == 2
    assert "fonts.googleapis.com/css2" in html
    assert "AA" in html  # contrast badge text


def test_recipe_only_board_renders_without_images() -> None:
    board = moodboard_from_kit(_kit(), business_name="Bean & Gather", images=[])
    html = render_moodboard_html(board)
    assert "<img " not in html
    assert "Recipe-only kit" in html  # graceful empty-imagery state


def test_render_guards_against_unfilled_tokens() -> None:
    # A leaked scaffold token ({{UPPER_CASE}}) must trip the guard, not ship.
    board = moodboard_from_kit(_kit(), business_name="{{HERO_TITLE}}", images=[])
    with pytest.raises(ValueError, match="unfilled tokens"):
        render_moodboard_html(board)
