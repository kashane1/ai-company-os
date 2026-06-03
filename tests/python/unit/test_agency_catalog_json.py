"""Drift guard: the committed BBW packages.json must equal the generator output."""

from __future__ import annotations

import json
from pathlib import Path

from packages.agency.catalog import load_catalog
from packages.agency.templates import render_catalog_json

REPO = Path(__file__).resolve().parents[3]
PACKAGES_JSON = REPO / "products" / "better-business-web" / "site" / "src" / "data" / "packages.json"


def test_committed_packages_json_matches_generator() -> None:
    catalog = load_catalog()
    expected = json.dumps(render_catalog_json(catalog), indent=2) + "\n"
    actual = PACKAGES_JSON.read_text(encoding="utf-8")
    assert actual == expected, (
        "products/better-business-web/site/src/data/packages.json is stale — run "
        "`python scripts/agency/render_catalog_json.py` and commit the result."
    )


def test_packages_json_hits_bundle_targets() -> None:
    data = render_catalog_json(load_catalog())
    by_id = {b["id"]: b for b in data["bundles"]}
    assert (by_id["package_a"]["setup"], by_id["package_a"]["monthly"]) == (699, 49)
    assert (by_id["package_b"]["setup"], by_id["package_b"]["monthly"]) == (999, 99)
    assert (by_id["package_c"]["setup"], by_id["package_c"]["monthly"]) == (1399, 249)
