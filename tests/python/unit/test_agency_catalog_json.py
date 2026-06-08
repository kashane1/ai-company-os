"""Drift guard: the committed BBW packages.json must equal the generator output."""

from __future__ import annotations

import json
from pathlib import Path

from packages.agency.catalog import load_catalog
from packages.agency.templates import render_catalog_json

REPO = Path(__file__).resolve().parents[3]
PACKAGES_JSON = (
    REPO / "products" / "better-business-web" / "site" / "src" / "data" / "packages.json"
)


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
    # Curated promo setups + monthlies (integer cents), gross + after split.
    assert (
        by_id["package_a"]["setup_gross_cents"],
        by_id["package_a"]["setup_after_cents"],
        by_id["package_a"]["monthly_cents"],
    ) == (70000, 60000, 5000)
    assert (
        by_id["package_b"]["setup_gross_cents"],
        by_id["package_b"]["setup_after_cents"],
        by_id["package_b"]["monthly_cents"],
    ) == (113000, 90000, 9000)
    assert (
        by_id["package_c"]["setup_gross_cents"],
        by_id["package_c"]["setup_after_cents"],
        by_id["package_c"]["monthly_cents"],
    ) == (225000, 180000, 55000)  # monthly is the package's monthly_promo ($550), not the $560 sum
    # Legacy dollar keys (used by the landing-page cards) = the promo price.
    assert (by_id["package_a"]["setup"], by_id["package_a"]["monthly"]) == (600, 50)
    assert (by_id["package_b"]["setup"], by_id["package_b"]["monthly"]) == (900, 90)
    assert (by_id["package_c"]["setup"], by_id["package_c"]["monthly"]) == (1800, 550)


def test_savings_is_gross_minus_after() -> None:
    by_id = {b["id"]: b for b in render_catalog_json(load_catalog())["bundles"]}
    for pkg, expected in [("package_a", 10000), ("package_b", 23000), ("package_c", 45000)]:
        b = by_id[pkg]
        assert b["savings_cents"] == b["setup_gross_cents"] - b["setup_after_cents"]
        assert b["savings_cents"] == expected


def test_custom_cart_of_preset_services_prices_higher_than_promo() -> None:
    catalog = load_catalog()
    for pkg, promo_after, monthly_sum in [
        ("package_a", 60000, 5000),
        ("package_b", 90000, 9000),
        ("package_c", 180000, 56000),  # custom cart pays the full $560 monthly sum...
    ]:
        custom = catalog.quote_services(catalog.bundles[pkg].service_ids)
        promo = catalog.quote_bundle(pkg)
        assert custom.pricing_mode == "tier"
        assert custom.setup_after_cents > promo_after  # package is the best setup value
        assert custom.monthly_cents == monthly_sum  # à-la-carte monthly = plain component sum
        # ...while the named package's monthly_promo makes the bundle the best monthly deal too.
        assert promo.monthly_cents <= custom.monthly_cents


def test_services_payload_and_discount_tiers_present() -> None:
    data = render_catalog_json(load_catalog())
    assert {s["id"] for s in data["services"]} >= {"website", "google_ads", "local_seo"}
    assert all("setup_cents" in s and "self_serve" in s for s in data["services"])
    assert data["discount_tiers"] == [
        {"min": 1, "max": 2, "pct": 0},
        {"min": 3, "max": 4, "pct": 10},
        {"min": 5, "max": None, "pct": 15},
    ]
