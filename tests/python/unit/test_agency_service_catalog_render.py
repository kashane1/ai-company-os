"""Drift guard: the committed catalog mirror must equal the generator output."""

from __future__ import annotations

from pathlib import Path

from packages.agency.catalog import load_catalog
from packages.agency.templates import _headline_price, render_service_catalog

MIRROR = Path(__file__).resolve().parents[3] / "docs" / "agency" / "service-catalog.md"


def test_committed_mirror_matches_generator() -> None:
    catalog = load_catalog()
    expected = render_service_catalog(catalog)
    actual = MIRROR.read_text(encoding="utf-8")
    assert actual == expected, (
        "docs/agency/service-catalog.md is stale — run "
        "`python scripts/agency/render_catalog_md.py` and commit the result."
    )


def test_generator_reflects_bundle_quotes() -> None:
    catalog = load_catalog()
    rendered = render_service_catalog(catalog)
    # Bundle anchors must appear exactly as quote_bundle computes them.
    for bundle_id in ("package_a", "package_b", "package_c"):
        quote = catalog.quote_bundle(bundle_id)
        anchor = _headline_price(quote)
        assert anchor in rendered, f"{bundle_id} anchor {anchor!r} missing from render"
