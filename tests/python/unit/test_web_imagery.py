"""Tests for the concept-led imagery pipeline (design engine Phase 4).

Locks the testable core: cohesive briefs (one shared style spec + a seed family),
manifest round-trip, and the provenance/clearance gate that keeps uncleared
generated imagery off a production client ship. Live Gemini generation is wrapped
in the CLI and verified manually (needs an API key).
"""

from __future__ import annotations

from packages.web.design_studio import WebsiteDesignRequest, build_design_studio_packet
from packages.web.imagery import (
    PROVENANCE_GENERATED,
    PROVENANCE_LICENSED,
    PROVENANCE_OWNER,
    ImageAsset,
    ImageryManifest,
    build_image_briefs,
    clearance_blockers,
    imagery_cleared,
    style_spec,
)

PACKET = build_design_studio_packet(
    WebsiteDesignRequest(
        site_name="TrueLine Plumbing",
        business_category="plumbing",
        audience="homeowners",
        goal="win trust",
        concept_statement="precision you can see; the calm craftsman",
    )
)


def test_briefs_are_cohesive_hero_plus_supporting_with_shared_style() -> None:
    briefs = build_image_briefs(PACKET, supporting=4)
    assert briefs[0].role == "hero"
    assert sum(b.role == "supporting" for b in briefs) == 4
    spec = style_spec(PACKET)
    # Every brief carries the same style spec → reads as one shoot.
    assert all(spec in b.prompt for b in briefs)
    # Distinct seeds across the set (a seed family, not one repeated value).
    seeds = [b.seed for b in briefs]
    assert len(set(seeds)) == len(seeds)


def test_manifest_round_trips(tmp_path) -> None:
    manifest = ImageryManifest(
        assets=[
            ImageAsset(id="hero", role="hero", path="/x/hero.png", provenance=PROVENANCE_GENERATED)
        ]
    )
    path = manifest.save(tmp_path / "manifest.json")
    again = ImageryManifest.load(path)
    assert again.assets[0].id == "hero"
    assert again.assets[0].provenance == PROVENANCE_GENERATED


def test_invalid_provenance_is_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        ImageAsset(id="x", role="hero", path="/x.png", provenance="stolen")


def test_clearance_blockers_only_flags_selected_generated_uncleared() -> None:
    manifest = ImageryManifest(
        assets=[
            ImageAsset(id="gen-uncleared", role="hero", path="a", provenance=PROVENANCE_GENERATED),
            ImageAsset(
                id="gen-cleared", role="supporting", path="b",
                provenance=PROVENANCE_GENERATED, production_clearance=True, cleared_by="founder",
            ),
            ImageAsset(id="gen-dropped", role="supporting", path="c",
                       provenance=PROVENANCE_GENERATED, selected=False),
            ImageAsset(id="owned", role="supporting", path="d", provenance=PROVENANCE_OWNER),
            ImageAsset(id="licensed", role="supporting", path="e", provenance=PROVENANCE_LICENSED),
        ]
    )
    blockers = clearance_blockers(manifest)
    assert blockers == ["gen-uncleared"]


def test_imagery_cleared_gate(tmp_path) -> None:
    mpath = tmp_path / "manifest.json"
    # No manifest → nothing to clear → cleared.
    assert imagery_cleared(mpath) is True

    ImageryManifest(
        assets=[ImageAsset(id="hero", role="hero", path="a", provenance=PROVENANCE_GENERATED)]
    ).save(mpath)
    assert imagery_cleared(mpath) is False  # uncleared generated asset

    ImageryManifest(
        assets=[
            ImageAsset(id="hero", role="hero", path="a", provenance=PROVENANCE_GENERATED,
                       production_clearance=True, cleared_by="founder")
        ]
    ).save(mpath)
    assert imagery_cleared(mpath) is True


def test_generate_imagery_set_curates_and_writes_manifest(tmp_path) -> None:
    # The loop's imagery leg: generate a hero + supporting set, auto-curate to top-N,
    # persist the manifest — all without an API key (generator injected).
    from packages.web.imagery import generate_imagery_set

    class _StubImage:
        def save(self, path):
            from pathlib import Path

            Path(path).write_bytes(b"\x89PNG\r\n\x1a\n")
            return path

    calls = []

    def gen(prompt, aspect_ratio, seed):
        calls.append((aspect_ratio, seed))
        return _StubImage()

    manifest = generate_imagery_set(PACKET, tmp_path, generate=gen, supporting=4, keep=3)
    assert len(calls) == 5  # 1 hero + 4 supporting
    assert len(manifest.assets) == 5
    selected = [a for a in manifest.assets if a.selected]
    assert len(selected) == 3  # auto-curated to the top 3
    assert any(a.role == "hero" and a.selected for a in manifest.assets)
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "hero.png").exists()


def test_imagery_direction_steers_hero_and_style() -> None:
    # The art-direction string drives the hero composition (instead of the generic
    # "composed scene") and is carried through the shared style spec for the whole set.
    from packages.web.design_studio import WebsiteDesignRequest, build_design_studio_packet
    from packages.web.imagery import build_image_briefs, style_spec

    packet = build_design_studio_packet(
        WebsiteDesignRequest(
            site_name="Pelican & Lime",
            business_category="fish taco restaurant",
            audience="beachgoers",
            goal="crave",
            imagery_direction="an abundant overhead flat-lay of fresh fish tacos",
        )
    )
    assert "overhead flat-lay" in style_spec(packet)
    hero = build_image_briefs(packet)[0]
    assert "overhead flat-lay" in hero.prompt
    assert "composed scene" not in hero.prompt
