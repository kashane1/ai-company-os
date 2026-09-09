"""Phase 5.3 — product registry phase field + projection writer tests."""

from __future__ import annotations

import json
from pathlib import Path

from packages.schemas.product import ProductConfig, ProductPhase, ProductPlatform
from packages.tools.product_artifacts.projection import (
    projection_path,
    write_projection,
)


def _make_config(phase: ProductPhase = ProductPhase.MVP_BUILD) -> ProductConfig:
    return ProductConfig(
        id="widget",
        name="Widget",
        slug="widget",
        platform=ProductPlatform.IOS,
        repo_id="widget-ios",
        source_path="/tmp/src",
        docs_root="/tmp/docs",
        phase=phase,
    )


def test_write_projection_round_trip(tmp_path: Path):
    config = _make_config(phase=ProductPhase.APP_STORE_SUBMISSION)
    path = write_projection(
        state_root=tmp_path,
        config=config,
        open_tasks=3,
        last_touched_at="2026-04-10T12:00:00Z",
        blockers=["waiting on founder approval"],
    )
    assert path == projection_path(tmp_path, "widget")
    data = json.loads(path.read_text())
    assert data["phase"] == "app-store-submission"
    assert data["open_tasks"] == 3
    assert data["blockers"] == ["waiting on founder approval"]


def test_phase_defaults_to_discovery_when_unset():
    config = ProductConfig(
        id="x",
        name="X",
        slug="x",
        platform=ProductPlatform.IOS,
        repo_id="x-ios",
        source_path="/tmp",
        docs_root="/tmp",
    )
    assert config.phase is ProductPhase.DISCOVERY


def test_infra_products_json_parses_phase():
    import json as _json
    from pathlib import Path as _Path

    infra = _Path(__file__).parent.parent.parent.parent / "infra" / "products.json"
    entries = _json.loads(infra.read_text())
    phases = {e["id"]: e.get("phase") for e in entries}
    assert phases["catchbook"] == "app-store-submission"
    assert phases["life-clock"] == "app-store-submission"
    assert phases["after-plans"] == "mvp-build"


def test_ios_registry_sources_match_managed_product_trees():
    repo_root = Path(__file__).parents[3]
    entries = json.loads((repo_root / "infra" / "products.json").read_text())

    ios_entries = {
        entry["id"]: entry
        for entry in entries
        if entry["platform"] == ProductPlatform.IOS.value
    }
    assert set(ios_entries) == {"catchbook", "life-clock", "after-plans"}

    for product_id, entry in ios_entries.items():
        source_root = repo_root / entry["source_path"]
        docs_root = repo_root / entry["docs_root"]

        assert source_root == repo_root / "products" / f"{product_id}-ios"
        assert (source_root / "project.yml").is_file()
        assert docs_root == repo_root / "docs" / "products" / product_id
        assert docs_root.is_dir()
