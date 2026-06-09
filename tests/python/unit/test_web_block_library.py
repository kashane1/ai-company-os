"""Tests for the block library (the growable design-space registry).

Locks the contract that lets the loop's search space grow safely: the registry
mirrors the imagery manifest (provenance + clearance), and feeding the composer a
library seeded from the builtins changes nothing — so admitting a new block is purely
additive, and an un-cleared generated block can never silently enter a build.
"""

from __future__ import annotations

import pytest

from packages.web.block_library import (
    SOURCE_HAND,
    SOURCE_STITCH,
    TIER_FLEET,
    TIER_PREMIUM,
    BlockEntry,
    BlockLibrary,
    clearance_blockers,
    library_cleared,
)
from packages.web.blocks_composer import (
    builtin_library,
    plan_composition,
    render_index_astro,
)
from packages.web.design_studio import WebsiteDesignRequest, build_design_studio_packet

PACKET = build_design_studio_packet(
    WebsiteDesignRequest(
        site_name="TrueLine Plumbing",
        business_category="plumbing",
        audience="homeowners",
        goal="win high-trust local work",
        evidence=["reviews praise careful cleanup", "20 years in business"],
        concept_statement="precision you can see; the calm craftsman",
    )
)
ARCHETYPE = PACKET.archetype


def _stitch_hero(*, cleared: bool = True, tier: str = TIER_FLEET) -> BlockEntry:
    return BlockEntry(
        id="stitch:hero-abc123",
        component="StitchHero",
        component_path="../blocks/generated/StitchHero.astro",
        slot="hero",
        archetype_affinity=(ARCHETYPE,),
        source=SOURCE_STITCH,
        license="generated",
        judge_score=4.2,
        tier=tier,
        cleared=cleared,
    )


# --------------------------------------------------------------------------- #
# Registry shape
# --------------------------------------------------------------------------- #
def test_builtin_library_has_one_cleared_hand_entry_per_builtin() -> None:
    lib = builtin_library()
    assert len(lib.entries) == 6
    assert {e.component for e in lib.entries} == {
        "CinematicHero", "EditorialSplit", "BentoGallery",
        "StickyProcess", "FullBleedMedia", "ClosingCta",
    }
    assert all(e.source == SOURCE_HAND and e.cleared for e in lib.entries)
    # The hero block serves the cinematic archetype; affinity is populated.
    hero = next(e for e in lib.entries if e.slot == "hero")
    assert ARCHETYPE in hero.archetype_affinity


def test_invalid_slot_source_tier_rejected() -> None:
    for bad in (
        {"slot": "banner"},
        {"source": "midjourney"},
        {"tier": "gold"},
    ):
        kwargs = {"id": "x", "component": "X", "component_path": "p", "slot": "hero"}
        kwargs.update(bad)
        with pytest.raises(ValueError):
            BlockEntry(**kwargs)


def test_save_load_round_trip(tmp_path) -> None:
    lib = builtin_library()
    lib.add(_stitch_hero())
    path = lib.save(tmp_path / "block-library" / "manifest.json")
    again = BlockLibrary.load(path)
    assert again.to_dict() == lib.to_dict()
    # affinity survives the JSON list -> tuple round trip
    assert all(isinstance(e.archetype_affinity, tuple) for e in again.entries)


# --------------------------------------------------------------------------- #
# Candidate filtering + resolution
# --------------------------------------------------------------------------- #
def test_candidates_filter_by_slot_affinity_and_clearance() -> None:
    lib = builtin_library()
    lib.add(_stitch_hero())
    heroes = {e.component for e in lib.candidates("hero", ARCHETYPE)}
    assert heroes == {"CinematicHero", "StitchHero"}
    # an archetype the stitch block does not serve only sees the builtin
    other = "gallery-led" if ARCHETYPE != "gallery-led" else "product-led"
    assert {e.component for e in lib.candidates("hero", other)} == {"CinematicHero"}


def test_uncleared_block_is_never_a_candidate() -> None:
    lib = BlockLibrary(entries=[_stitch_hero(cleared=False)])
    assert lib.candidates("hero", ARCHETYPE) == []
    assert lib.resolve("hero", ARCHETYPE) is None


def test_fleet_build_cannot_see_premium_blocks() -> None:
    lib = BlockLibrary(entries=[_stitch_hero(tier=TIER_PREMIUM)])
    assert lib.candidates("hero", ARCHETYPE, tier=TIER_FLEET) == []
    assert [e.component for e in lib.candidates("hero", ARCHETYPE, tier=TIER_PREMIUM)] == [
        "StitchHero"
    ]


def test_resolve_is_deterministic() -> None:
    lib = builtin_library()
    lib.add(_stitch_hero())
    first = lib.resolve("hero", ARCHETYPE, concept=PACKET.concept_statement)
    second = lib.resolve("hero", ARCHETYPE, concept=PACKET.concept_statement)
    assert first is not None and first.id == second.id


# --------------------------------------------------------------------------- #
# Clearance gate (mirrors imagery)
# --------------------------------------------------------------------------- #
def test_clearance_blockers_lists_uncleared_generated_only() -> None:
    lib = builtin_library()  # all hand, all cleared
    assert clearance_blockers(lib) == []
    lib.add(_stitch_hero(cleared=False))
    assert clearance_blockers(lib) == ["stitch:hero-abc123"]
    lib.add(_stitch_hero(cleared=True))  # same id, now cleared -> no longer blocks
    assert clearance_blockers(lib) == []


def test_library_cleared_file_gate(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    assert library_cleared(path) is True  # no library -> nothing to clear
    BlockLibrary(entries=[_stitch_hero(cleared=False)]).save(path)
    assert library_cleared(path) is False
    BlockLibrary(entries=[_stitch_hero(cleared=True)]).save(path)
    assert library_cleared(path) is True


# --------------------------------------------------------------------------- #
# Composer integration — the zero-behaviour-change guarantee
# --------------------------------------------------------------------------- #
def test_builtin_library_compose_equals_no_library() -> None:
    base = plan_composition(PACKET)
    via_lib = plan_composition(PACKET, library=builtin_library())
    assert [b.component for b in base.blocks] == [b.component for b in via_lib.blocks]
    # rendered output is byte-for-byte identical (import paths fall back to builtins)
    assert render_index_astro(base) == render_index_astro(via_lib)


def test_admitted_block_replaces_builtin_in_its_slot() -> None:
    # A library where the only hero candidate is the stitch block.
    lib = BlockLibrary(
        entries=[e for e in builtin_library().entries if e.slot != "hero"] + [_stitch_hero()]
    )
    comp = plan_composition(PACKET, library=lib)
    assert comp.blocks[0].component == "StitchHero"
    assert comp.blocks[0].import_path == "../blocks/generated/StitchHero.astro"
    # its custom import path is wired into the generated index.astro
    assert "../blocks/generated/StitchHero.astro" in render_index_astro(comp)


def test_uncleared_admission_falls_back_to_builtin_in_compose() -> None:
    lib = BlockLibrary(
        entries=[e for e in builtin_library().entries if e.slot != "hero"]
        + [_stitch_hero(cleared=False)]
    )
    comp = plan_composition(PACKET, library=lib)
    # the uncleared block is invisible; the builtin hero is used instead
    assert comp.blocks[0].component == "CinematicHero"
