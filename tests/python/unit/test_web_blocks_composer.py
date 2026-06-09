"""Tests for the block composer (design engine Phase 3).

The composer is the deterministic brain that decides which art-directed blocks
appear, in what order, with what content — so a build escapes the stacked template
by construction. We can't assert "the layout looks good" (the rubric does that),
but we lock the structural contract.
"""

from __future__ import annotations

import json

from packages.web.blocks_composer import plan_composition, render_index_astro
from packages.web.design_studio import WebsiteDesignRequest, build_design_studio_packet

CINEMATIC = build_design_studio_packet(
    WebsiteDesignRequest(
        site_name="TrueLine Plumbing",
        business_category="plumbing",
        audience="homeowners",
        goal="win high-trust local work",
        evidence=["reviews praise careful cleanup", "20 years in business"],
        concept_statement="precision you can see; the calm craftsman",
    )
)
GALLERY = build_design_studio_packet(
    WebsiteDesignRequest(
        site_name="Lumiere Nail Lounge",
        business_category="nail salon",
        audience="clients choosing by visual proof",
        goal="show artistry",
    )
)


def test_plan_opens_on_hero_and_closes_on_cta() -> None:
    comp = plan_composition(CINEMATIC)
    assert comp.blocks[0].component == "CinematicHero"
    assert comp.blocks[-1].component == "ClosingCta"


def test_archetypes_get_different_compositions() -> None:
    cine = [b.component for b in plan_composition(CINEMATIC).blocks]
    gal = [b.component for b in plan_composition(GALLERY).blocks]
    # Not the same stacked template: cinematic leads with process/editorial,
    # gallery leads with the bento grid.
    assert cine != gal
    assert "StickyProcess" in cine
    assert gal.index("BentoGallery") < gal.index("EditorialSplit")


def test_blocks_are_filled_with_packet_content() -> None:
    comp = plan_composition(CINEMATIC)
    hero = next(b for b in comp.blocks if b.component == "CinematicHero")
    assert hero.data["headline"]  # non-empty
    # Real evidence flows into proof points.
    split = next(b for b in comp.blocks if b.component == "EditorialSplit")
    assert any("cleanup" in p for p in split.data["points"])


def test_explicit_content_overrides_derived() -> None:
    comp = plan_composition(CINEMATIC, content={"hero": {"headline": "Custom line"}})
    hero = next(b for b in comp.blocks if b.component == "CinematicHero")
    assert hero.data == {"headline": "Custom line"}


def test_render_produces_valid_astro_importing_used_blocks() -> None:
    comp = plan_composition(CINEMATIC)
    astro = render_index_astro(comp, tagline="Plumbing done with precision")

    import re

    assert astro.startswith("---")
    # No leftover {{SCAFFOLD_TOKENS}}. (data={{...}} is valid Astro object-prop
    # syntax, so we check for the UPPERCASE token pattern specifically.)
    assert not re.search(r"\{\{[A-Z_]+\}\}", astro)
    assert 'import "../scripts/motion.ts";' in astro
    assert "TrueLine Plumbing" in astro
    # Every placed component is imported exactly once and rendered with a data prop.
    for comp_name in {b.component for b in comp.blocks}:
        assert f"import {comp_name} from" in astro
        assert astro.count(f"import {comp_name} from") == 1
        assert f"<{comp_name} data={{" in astro


def test_render_embeds_valid_json_data() -> None:
    comp = plan_composition(CINEMATIC)
    hero = next(b for b in comp.blocks if b.component == "CinematicHero")
    astro = render_index_astro(comp)
    # The serialized data round-trips as JSON (valid JS object literal in the prop).
    assert json.dumps(hero.data) in astro
