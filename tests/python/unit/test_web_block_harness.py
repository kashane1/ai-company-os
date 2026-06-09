"""Tests for the single-block render harness."""

from __future__ import annotations

from packages.web.block_harness import harness_index_astro, sample_data_for
from packages.web.block_tournament import BlockCandidate


def _candidate(slot: str = "hero", component: str = "GenHero") -> BlockCandidate:
    return BlockCandidate(
        id="c1", slot=slot, component=component, source="stitch", astro="<section/>"
    )


def test_harness_imports_only_the_candidate_from_its_generated_path() -> None:
    astro = harness_index_astro(_candidate(component="StitchHeroA1"))
    assert 'import StitchHeroA1 from "../blocks/generated/StitchHeroA1.astro";' in astro
    assert "<StitchHeroA1 data=" in astro
    # one block only — no other block components imported
    assert astro.count("../blocks/generated/") == 1


def test_harness_injects_slot_sample_data() -> None:
    astro = harness_index_astro(_candidate(slot="hero"))
    assert "Work you can point to." in astro  # hero sample headline


def test_sample_data_covers_every_slot() -> None:
    for slot in ("hero", "split", "bento", "process", "fullbleed", "cta"):
        assert sample_data_for(slot), f"no sample data for slot {slot}"
