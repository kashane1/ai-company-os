"""Tests for the reference analyzer core (design engine Phase 5)."""

from __future__ import annotations

import pytest

from packages.web.reference_params import (
    ReferenceParams,
    apply_to_spec,
    palette_from_image,
    params_to_takeaways,
    recommended_variant,
)

RAMOTION = ReferenceParams(
    title="HackerRank B2B SaaS",
    url="https://dribbble.com/shots/26414267",
    palette=["#0b0b0b", "#39ff7a"],
    type_scale_ratio=1.333,
    density="dense",
    grid="device-frame",
    hero_structure="large device-frame over black",
    motion_cues=["scroll-pinned device"],
    takeaways=["single strong visual thesis"],
)


def test_invalid_palette_hex_is_rejected() -> None:
    with pytest.raises(ValueError):
        ReferenceParams(title="x", palette=["var(--nope)"])


def test_implausible_ratio_and_density_are_rejected() -> None:
    with pytest.raises(ValueError):
        ReferenceParams(title="x", type_scale_ratio=9.0)
    with pytest.raises(ValueError):
        ReferenceParams(title="x", density="loud")


def test_params_to_takeaways_translates_structure() -> None:
    out = params_to_takeaways(RAMOTION)
    assert "single strong visual thesis" in out
    assert any("dense density" in t and "device-frame grid" in t for t in out)
    assert any(t.startswith("hero:") for t in out)
    assert any(t.startswith("motion:") for t in out)


def test_apply_to_spec_seeds_palette_and_appends_reference() -> None:
    spec = {"site_name": "Acme", "business_category": "saas", "audience": "teams", "goal": "x"}
    merged = apply_to_spec(RAMOTION, spec)
    # Reference dominant color seeds the concept palette (business cue would win).
    assert merged["concept_palette"] == "#0b0b0b"
    assert merged["references"][0]["title"] == "HackerRank B2B SaaS"
    assert merged["references"][0]["takeaways"]
    # Input spec is not mutated.
    assert "concept_palette" not in spec


def test_apply_does_not_override_an_existing_business_palette() -> None:
    spec = {"site_name": "Acme", "concept_palette": "#123456", "business_category": "saas",
            "audience": "teams", "goal": "x"}
    merged = apply_to_spec(RAMOTION, spec)
    assert merged["concept_palette"] == "#123456"  # the business's own cue wins


def test_roundtrip_from_dict_ignores_unknown_keys() -> None:
    ref = ReferenceParams.from_dict({**RAMOTION.to_dict(), "junk": 1})
    assert ref.title == RAMOTION.title


def test_palette_from_image_extracts_dominant_color(tmp_path) -> None:
    # A real reference READ (v2 never ingested an image). A solid teal image yields
    # a teal-dominant palette.
    from PIL import Image

    path = tmp_path / "ref.png"
    Image.new("RGB", (64, 64), (18, 130, 130)).save(path)
    palette = palette_from_image(path, k=3)
    assert palette and all(c.startswith("#") for c in palette)
    r, g, b = int(palette[0][1:3], 16), int(palette[0][3:5], 16), int(palette[0][5:7], 16)
    assert g > 90 and b > 90 and r < 90  # teal-ish dominant


def test_recommended_variant_maps_hero_structure_to_layout() -> None:
    full = ReferenceParams(title="x", hero_structure="full-bleed cinematic image")
    editorial = ReferenceParams(title="y", hero_structure="editorial split, type-led")
    assert recommended_variant(full, 3) == 1  # image-led variant
    assert recommended_variant(editorial, 3) == 0  # clean editorial variant
    assert recommended_variant(full, 1) == 0  # single-variant archetype → only option


def test_reference_changes_layout_not_just_color() -> None:
    # The Phase 5 exit criterion: a reference's hero structure measurably changes the
    # composed skeleton (a full-bleed reference pulls in the FullBleedMedia block).
    from packages.web.blocks_composer import _VARIANTS, plan_composition
    from packages.web.design_studio import WebsiteDesignRequest, build_design_studio_packet

    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="Meridian", business_category="boutique fitness",
            audience="members", goal="book a first class",
            concept_statement="strength as ritual",
        )
    )
    n = len(_VARIANTS[packet.archetype])
    full = ReferenceParams(title="r", hero_structure="full-bleed image")
    editorial = ReferenceParams(title="r", hero_structure="editorial split")
    full_comp = plan_composition(packet, variant=recommended_variant(full, n))
    ed_comp = plan_composition(packet, variant=recommended_variant(editorial, n))
    full_plan = [b.component for b in full_comp.blocks]
    ed_plan = [b.component for b in ed_comp.blocks]
    assert "FullBleedMedia" in full_plan
    assert full_plan != ed_plan
