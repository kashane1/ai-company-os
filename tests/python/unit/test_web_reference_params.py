"""Tests for the reference analyzer core (design engine Phase 5)."""

from __future__ import annotations

import pytest

from packages.web.reference_params import (
    ReferenceParams,
    apply_to_spec,
    params_to_takeaways,
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
