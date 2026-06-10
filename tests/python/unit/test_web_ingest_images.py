"""Tests for the external-image ingest bridge (ChatGPT/owner images → imagery manifest)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from packages.web.imagery import ImageryManifest

_spec = importlib.util.spec_from_file_location(
    "ingest_images", Path(__file__).resolve().parents[3] / "scripts" / "web" / "ingest_images.py"
)
ingest_images = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ingest_images)


def _png(p: Path) -> Path:
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)  # a tiny non-empty file
    return p


def test_ingest_writes_a_loadable_manifest(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    hero = _png(src / "hero.png")
    s1 = _png(src / "a.png")
    s2 = _png(src / "b.png")
    target = tmp_path / "hub"

    manifest_path = ingest_images.ingest(target, hero, [s1, s2])

    m = ImageryManifest.load(manifest_path)
    assert [a.role for a in m.assets] == ["hero", "supporting", "supporting"]
    assert [a.id for a in m.assets] == ["hero", "support-1", "support-2"]
    # files were staged into the imagery dir and resolve
    for a in m.assets:
        assert Path(a.path).is_file()
        assert a.selected
    # owner provenance never blocks the build/clearance gate
    assert all(a.provenance == "owner" for a in m.assets)


def test_ingest_rejects_missing_file(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(FileNotFoundError):
        ingest_images.ingest(tmp_path / "hub", tmp_path / "nope.png", [])
