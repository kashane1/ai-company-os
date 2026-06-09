"""Tests for the imagery CLI's unattended curation (design engine v3 — Phase 1).

`select --auto-curate N` lets the autonomous loop curate without a human/agent:
keep the hero + the first N-1 supporting assets in seed order.
"""

from __future__ import annotations

from packages.web.imagery import ImageAsset, ImageryManifest
from scripts.agency.generate_imagery import _manifest_path, cmd_select


def _seed_manifest(target) -> None:
    ImageryManifest(
        assets=[
            ImageAsset(id="hero", role="hero", path="hero.png", provenance="generated"),
            ImageAsset(id="support-1", role="supporting", path="s1.png", provenance="generated"),
            ImageAsset(id="support-2", role="supporting", path="s2.png", provenance="generated"),
            ImageAsset(id="support-3", role="supporting", path="s3.png", provenance="generated"),
        ]
    ).save(_manifest_path(target))


def test_auto_curate_keeps_hero_plus_n_minus_one(tmp_path) -> None:
    _seed_manifest(tmp_path)
    rc = cmd_select(str(tmp_path), None, 2)
    assert rc == 0
    manifest = ImageryManifest.load(_manifest_path(tmp_path))
    selected = {a.id for a in manifest.assets if a.selected}
    assert selected == {"hero", "support-1"}


def test_explicit_keep_still_works(tmp_path) -> None:
    _seed_manifest(tmp_path)
    rc = cmd_select(str(tmp_path), ["hero", "support-3"], None)
    assert rc == 0
    manifest = ImageryManifest.load(_manifest_path(tmp_path))
    selected = {a.id for a in manifest.assets if a.selected}
    assert selected == {"hero", "support-3"}
