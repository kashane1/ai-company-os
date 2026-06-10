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


def test_classic_custom_has_a_process_led_variant() -> None:
    # med-spa-style wellness brands get a calm, process-led layout (a consult flow between
    # the split and the band) — structurally distinct from the bento-gallery demos.
    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="Lumina", business_category="med spa", audience="clients",
            goal="book consultations", evidence=["board-certified injectors"],
        )
    )
    assert packet.archetype == "classic-custom"
    names = [b.component for b in plan_composition(packet, variant=2).blocks]
    assert names == [
        "CinematicHero", "EditorialSplit", "StickyProcess", "FullBleedMedia", "ClosingCta",
    ]


def test_plan_opens_on_hero_and_closes_on_cta() -> None:
    comp = plan_composition(CINEMATIC)
    assert comp.blocks[0].component == "CinematicHero"
    assert comp.blocks[-1].component == "ClosingCta"


def test_archetypes_get_different_compositions() -> None:
    cine = [b.component for b in plan_composition(CINEMATIC).blocks]
    gal = [b.component for b in plan_composition(GALLERY).blocks]
    # Not the same stacked template; both still open on hero / close on CTA.
    assert cine != gal
    assert cine[0] == gal[0] == "CinematicHero"
    assert cine[-1] == gal[-1] == "ClosingCta"
    assert "BentoGallery" in gal  # the gallery archetype always features the grid


def test_variant_selection_is_deterministic() -> None:
    first = [b.component for b in plan_composition(CINEMATIC).blocks]
    second = [b.component for b in plan_composition(CINEMATIC).blocks]
    assert first == second  # same packet → same skeleton (no Math.random churn)


def test_different_concepts_yield_varied_skeletons() -> None:
    # The v3 fix for template-sameness: same archetype, different concepts → the
    # composer picks different structural variants (not one fixed section order).
    plans = set()
    for i in range(6):
        packet = build_design_studio_packet(
            WebsiteDesignRequest(
                site_name=f"Site {i}",
                business_category="plumbing",
                audience="homeowners",
                goal="win work",
                concept_statement=f"distinct concept number {i} with words {i * 7}",
            )
        )
        plans.add(tuple(b.component for b in plan_composition(packet).blocks))
    assert len(plans) >= 2  # not the same skeleton for every build


def test_images_populate_hero_gallery_and_fullbleed() -> None:
    images = {"hero": "/img/hero.png", "supporting": ["/img/s1.png", "/img/s2.png"]}
    comp = plan_composition(GALLERY, images=images)
    hero = next(b for b in comp.blocks if b.component == "CinematicHero")
    assert hero.data["image"] == "/img/hero.png"
    bento = next(b for b in comp.blocks if b.component == "BentoGallery")
    assert any(item.get("image") for item in bento.data["items"])


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


def test_no_duplicate_sections_when_fullbleed_is_present() -> None:
    # Regression: the hero and the full-bleed band must NOT share an image or headline
    # (the bug that rendered the hero twice). variant=1 forces the FullBleedMedia plan.
    from packages.web.blocks_composer import duplicate_sections

    images = {"hero": "/img/hero.png", "supporting": ["/img/s1.png", "/img/s2.png"]}
    comp = plan_composition(CINEMATIC, images=images, variant=1)
    assert "FullBleedMedia" in [b.component for b in comp.blocks]
    assert duplicate_sections(comp) == []
    hero = next(b for b in comp.blocks if b.component == "CinematicHero")
    band = next(b for b in comp.blocks if b.component == "FullBleedMedia")
    assert hero.data["image"] != band.data["image"]
    assert hero.data["headline"] != band.data["headline"]


def test_duplicate_sections_detects_a_repeated_hero() -> None:
    from packages.web.blocks_composer import BlockSpec, Composition, duplicate_sections

    comp = Composition(
        site_name="X",
        archetype="gallery-led",
        blocks=[
            BlockSpec("CinematicHero", {"image": "/img/h.png", "headline": "Same line"}),
            BlockSpec("FullBleedMedia", {"image": "/img/h.png", "headline": "Same line"}),
        ],
    )
    defects = duplicate_sections(comp)
    assert any("reuses the image" in d for d in defects)
    assert any("repeats" in d and "headline" in d for d in defects)


def test_duplicate_sections_detects_a_repeated_label() -> None:
    # The eyebrow/kicker label repeated across blocks is also a defect (the bug that
    # put "Fish Taco Restaurant" in both the hero eyebrow and the band kicker).
    from packages.web.blocks_composer import BlockSpec, Composition, duplicate_sections

    comp = Composition(
        site_name="X",
        archetype="editorial-visit",
        blocks=[
            BlockSpec("CinematicHero", {"image": "/a.png", "eyebrow": "Fish Taco Restaurant"}),
            BlockSpec("FullBleedMedia", {"image": "/b.png", "kicker": "Fish Taco Restaurant"}),
        ],
    )
    assert any("repeats" in d for d in duplicate_sections(comp))


def test_fullbleed_never_directly_after_cinematic_hero() -> None:
    # Two full-bleed photo sections back-to-back (hero is already full-bleed) read as a
    # cluttered, overlapping patchwork. No variant — and nothing the guard returns —
    # may place FullBleedMedia immediately after CinematicHero.
    from packages.web.blocks_composer import _VARIANTS, _separate_fullbleed_from_hero

    for archetype, variants in _VARIANTS.items():
        for v in variants:
            norm = _separate_fullbleed_from_hero(v)
            if norm and norm[0] == "CinematicHero":
                assert norm[1] != "FullBleedMedia", (archetype, norm)

    # The guard repairs a bad variant by swapping in the next contained section.
    fixed = _separate_fullbleed_from_hero(
        ["CinematicHero", "FullBleedMedia", "EditorialSplit", "ClosingCta"]
    )
    assert fixed == ["CinematicHero", "EditorialSplit", "FullBleedMedia", "ClosingCta"]


def test_bento_images_distinct_and_band_separate() -> None:
    # Regression: the bento used to cycle images (supplying < cells repeated photos) and
    # the full-bleed band reused bento cell 0's image. With enough supporting images the
    # bento cells must be distinct AND the band image must not appear in the bento.
    from packages.web.blocks_composer import derive_content

    imgs = {"hero": "/img/hero.png",
            "supporting": ["/img/a.png", "/img/b.png", "/img/c.png", "/img/d.png"]}
    content = derive_content(CINEMATIC, images=imgs)
    bento_imgs = [it["image"] for it in content["bento"]["items"] if it.get("image")]
    assert len(bento_imgs) == len(set(bento_imgs)), f"bento repeats: {bento_imgs}"
    band_img = content["fullbleed"]["image"]
    assert band_img not in bento_imgs, "band image duplicates a bento cell"


def test_bento_is_image_led_no_imageless_cards() -> None:
    # Image-led: with fewer proof IMAGES than proof points, the bento renders one card per
    # image (every card has a photo) instead of padding with a lone image-less card that
    # reads as a broken/missing photo. Extra proof points live in the split section.
    from packages.web.blocks_composer import derive_content

    imgs = {"hero": "/img/hero.png", "supporting": ["/img/a.png", "/img/b.png"]}
    content = derive_content(CINEMATIC, images=imgs)  # 1 reserved for band → 1 bento image
    items = content["bento"]["items"]
    assert items and all(it.get("image") for it in items), "every bento card must have an image"
    bento_imgs = [it["image"] for it in items]
    assert len(bento_imgs) == len(set(bento_imgs)), f"bento repeats: {bento_imgs}"
    assert content["fullbleed"]["image"] not in bento_imgs


def test_bento_caps_cards_to_images_when_proof_exceeds_photos() -> None:
    # The fish-taco case: 4 proof bullets but only 3 bento photos (the 4th supporting is
    # the band) → 3 image cards, no 4th image-less card.
    from packages.web.blocks_composer import derive_content

    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="Pelican & Lime", business_category="fish taco restaurant",
            audience="beachgoers", goal="drive orders",
            evidence=["wild-caught fish", "hand-pressed tortillas", "ocean-view patio", "crema"],
        )
    )
    imgs = {"hero": "/img/h.png",
            "supporting": ["/img/a.png", "/img/b.png", "/img/c.png", "/img/d.png"]}
    content = derive_content(packet, images=imgs)
    items = content["bento"]["items"]
    assert len(items) == 3  # one per bento image (a,b,c); d is the band
    assert all(it.get("image") for it in items)
