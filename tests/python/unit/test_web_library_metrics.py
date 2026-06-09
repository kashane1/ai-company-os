"""Tests for library metrics (the compounding signals)."""

from __future__ import annotations

from packages.web.block_library import BlockEntry, BlockLibrary, TIER_PREMIUM
from packages.web.blocks_composer import builtin_library
from packages.web.library_metrics import (
    block_usage,
    dominance_flags,
    library_report,
    pass_rate,
    score_spread,
    search_space_width,
    slot_coverage,
)


def _gen_hero(cleared: bool, tier: str = "fleet", cid: str = "stitch:hero-1") -> BlockEntry:
    return BlockEntry(
        id=cid, component="StitchHero", component_path="p", slot="hero",
        source="stitch", tier=tier, cleared=cleared,
    )


def test_slot_coverage_counts_only_cleared_eligible() -> None:
    lib = builtin_library()  # one cleared hand block per slot
    cov = slot_coverage(lib)
    assert cov["hero"] == 1 and cov["cta"] == 1
    lib.add(_gen_hero(cleared=False))  # un-cleared -> doesn't widen the space
    assert slot_coverage(lib)["hero"] == 1
    lib.add(_gen_hero(cleared=True))  # cleared -> now two hero options
    assert slot_coverage(lib)["hero"] == 2


def test_search_space_width_grows_with_cleared_blocks() -> None:
    lib = builtin_library()
    before = search_space_width(lib)
    lib.add(_gen_hero(cleared=True))
    assert search_space_width(lib) == before + 1


def test_premium_tier_sees_more_than_fleet() -> None:
    lib = builtin_library()
    lib.add(_gen_hero(cleared=True, tier=TIER_PREMIUM, cid="stitch:hero-premium"))
    assert search_space_width(lib, tier="fleet") < search_space_width(lib, tier="premium")


def test_block_usage_and_dominance() -> None:
    comps = [
        ["CinematicHero", "EditorialSplit", "ClosingCta"],
        ["CinematicHero", "BentoGallery", "ClosingCta"],
        ["CinematicHero", "EditorialSplit", "ClosingCta"],
    ]
    usage = block_usage(comps)
    assert usage["CinematicHero"] == 3
    # CinematicHero is in every build but not >60% of all placements
    assert "CinematicHero" not in dominance_flags(usage, threshold=0.6)
    # a degenerate set where one block dominates IS flagged
    assert dominance_flags(block_usage([["X"], ["X"], ["X", "Y"]]), threshold=0.6) == ["X"]


def test_pass_rate_and_score_spread() -> None:
    assert pass_rate([True, True, False, True]) == 0.75
    assert pass_rate([]) == 0.0
    spread = score_spread([80, 90, 100])
    assert spread["min"] == 80 and spread["max"] == 100 and spread["mean"] == 90.0


def test_library_report_bundles_metrics() -> None:
    lib = builtin_library()
    report = library_report(lib, compositions=[["CinematicHero", "ClosingCta"]])
    assert report["blocks_total"] == 6
    assert report["search_space_width"] == 6
    assert report["block_usage"]["CinematicHero"] == 1
    assert "dominance_flags" in report
