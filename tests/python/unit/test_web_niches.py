"""Tests for the premium niche → starter spec helper (design engine v3 — Phase 5)."""

from __future__ import annotations

from packages.web.design_studio import build_design_studio_packet
from packages.web.niches import catalog_niches, niche_to_spec
from scripts.agency.design_studio import request_from_spec


def test_catalog_match_returns_niche_spec() -> None:
    spec = niche_to_spec("med spa")
    assert spec["business_category"] == "med spa"
    assert spec["concept_statement"]
    assert spec["evidence"]


def test_match_is_substring_and_case_insensitive() -> None:
    assert niche_to_spec("Boutique Fitness Studio")["business_category"] == "boutique fitness"
    assert niche_to_spec("PILATES")["business_category"] == "boutique fitness"


def test_unknown_niche_falls_back_to_generic_spec() -> None:
    spec = niche_to_spec("artisan candle shop")
    assert "candle" in str(spec["business_category"]).lower()
    assert spec["concept_statement"]


def test_every_catalog_spec_builds_a_valid_packet() -> None:
    # A niche spec must round-trip into a real art-direction packet (so `make premium
    # NICHE=...` can run end to end).
    for niche in catalog_niches():
        packet = build_design_studio_packet(request_from_spec(niche_to_spec(niche)))
        assert packet.site_name and packet.archetype and packet.concept_statement
