"""Phase 5.1 — product-artifact-chain validator tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.tools.product_artifacts.validator import validate_chain


def _seed(dir: Path, files: dict[str, str]) -> None:
    dir.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (dir / name).write_text(body)


def test_full_chain_ok(tmp_path: Path):
    product_dir = tmp_path / "widget"
    _seed(
        product_dir,
        {
            "founder-brief.md": "# Widget\nThe founder brief.\n",
            "product-brief.md": "# Product brief\nBuilds on founder-brief.md.\n",
            "mvp-spec.md": "# MVP spec\nBased on product-brief.md.\n",
            "monetization-strategy.md": "# Monetization\nDerived from product-brief.md.\n",
            "app-store-positioning.md": "# Positioning\nPulls from product-brief.md and mvp-spec.md.\n",
            "appstore-metadata-draft.md": "# Metadata\nFrom app-store-positioning.md.\n",
            "submission-checklist.md": "# Checklist\nSee appstore-metadata-draft.md.\n",
        },
    )
    report = validate_chain(product_id="widget", product_dir=product_dir, phase="app-store-submission")
    assert report.ok, report.violations
    assert "founder-brief" in report.present_nodes
    assert "submission-checklist" in report.present_nodes
    assert report.missing_nodes == ()


def test_missing_node_flagged_for_current_phase(tmp_path: Path):
    product_dir = tmp_path / "half-widget"
    _seed(
        product_dir,
        {
            "founder-brief.md": "brief",
            "product-brief.md": "founder-brief.md",
        },
    )
    report = validate_chain(
        product_id="half-widget",
        product_dir=product_dir,
        phase="app-store-submission",
    )
    assert not report.ok
    codes = {v.code for v in report.violations}
    assert "missing_required_node" in codes
    assert "submission-checklist" in report.missing_nodes


def test_missing_node_ignored_in_earlier_phase(tmp_path: Path):
    product_dir = tmp_path / "discovery-only"
    _seed(
        product_dir,
        {
            "founder-brief.md": "brief",
            "product-brief.md": "references founder-brief.md",
        },
    )
    report = validate_chain(
        product_id="discovery-only",
        product_dir=product_dir,
        phase="discovery",
    )
    # mvp-spec etc. should NOT be flagged as missing at discovery phase.
    assert report.missing_nodes == ()
    assert report.ok


def test_parent_reference_missing(tmp_path: Path):
    product_dir = tmp_path / "orphan"
    _seed(
        product_dir,
        {
            "founder-brief.md": "brief",
            "product-brief.md": "standalone, does not link back",
        },
    )
    report = validate_chain(
        product_id="orphan",
        product_dir=product_dir,
        phase="discovery",
    )
    assert any(v.code == "parent_reference_missing" for v in report.violations)
