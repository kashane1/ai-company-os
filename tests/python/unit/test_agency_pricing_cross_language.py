"""Cross-language drift guard: the JS pricing helper must match Python to the cent.

Feeds identical inputs (per-service cents + discount tiers) to both Python
``quote_services`` and the shared JS ``quoteServices`` (run via node), and asserts
byte-identical integer results across representative carts — including a synthetic
half-cent fixture the real catalog doesn't contain. Skips if node is unavailable,
mirroring the existing node-fallback pattern in the billing-poller tests.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from packages.agency.catalog import load_catalog
from packages.schemas.offer import (
    BillType,
    DiscountTier,
    Service,
    ServiceCatalog,
    ServiceTier,
    to_cents,
)

REPO = Path(__file__).resolve().parents[3]
RUNNER = REPO / "products" / "better-business-web" / "site" / "scripts" / "pricing-golden.mjs"

# A synthetic service whose setup (5c) forces a half-cent at the 10% tier.
_SYNTH = ServiceCatalog(
    services={
        "p5": Service("p5", "P5", ServiceTier.TIER_1, BillType.ONE_TIME, setup_fee=0.05),
    },
    bundles={},
    discount_tiers=(DiscountTier(1, None, 10),),
)


def _services_map(catalog: ServiceCatalog) -> dict[str, dict[str, int]]:
    return {
        sid: {"setup_cents": to_cents(s.setup_fee), "monthly_cents": to_cents(s.monthly_fee)}
        for sid, s in catalog.services.items()
    }


def _tiers_payload(catalog: ServiceCatalog) -> list[dict[str, object]]:
    return [
        {"min": t.min_services, "max": t.max_services, "pct": t.pct}
        for t in catalog.discount_tiers
    ]


def _carts(catalog: ServiceCatalog) -> list[dict[str, object]]:
    a = catalog.bundles["package_a"]
    b = catalog.bundles["package_b"]
    c = catalog.bundles["package_c"]
    return [
        # presets at their promo (override)
        {"service_ids": a.service_ids, "setup_promo_cents": to_cents(a.setup_promo)},
        {"service_ids": b.service_ids, "setup_promo_cents": to_cents(b.setup_promo)},
        {"service_ids": c.service_ids, "setup_promo_cents": to_cents(c.setup_promo)},
        # the SAME sets as custom carts (tier discount, no override)
        {"service_ids": a.service_ids, "setup_promo_cents": None},
        {"service_ids": b.service_ids, "setup_promo_cents": None},
        {"service_ids": c.service_ids, "setup_promo_cents": None},
        # 1 / setup-only carts
        {"service_ids": ["website"], "setup_promo_cents": None},
        {"service_ids": ["website", "gbp", "business_email"], "setup_promo_cents": None},
    ]


def _python_quote(catalog: ServiceCatalog, cart: dict[str, object]) -> dict[str, int]:
    q = catalog.quote_services(
        list(cart["service_ids"]), setup_promo_cents=cart["setup_promo_cents"]
    )
    return {
        "setupGrossCents": q.setup_gross_cents,
        "setupAfterCents": q.setup_after_cents,
        "monthlyCents": q.monthly_cents,
        "savingsCents": q.savings_cents,
        "tierPct": q.tier_pct,
        "pricingMode": q.pricing_mode,
    }


def _run_node(payload: dict[str, object]) -> list[dict[str, object]]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    proc = subprocess.run(
        [node, str(RUNNER)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_js_pricing_matches_python_on_real_catalog() -> None:
    catalog = load_catalog()
    carts = _carts(catalog)
    payload = {
        "carts": carts,
        "services": _services_map(catalog),
        "tiers": _tiers_payload(catalog),
    }
    js = _run_node(payload)
    py = [_python_quote(catalog, cart) for cart in carts]
    assert js == py


def test_js_pricing_matches_python_on_half_cent() -> None:
    # gross 5c, 10% tier -> 0.5c discount -> half-up to 1c (banker's would be 0).
    carts = [{"service_ids": ["p5"], "setup_promo_cents": None}]
    payload = {
        "carts": carts,
        "services": _services_map(_SYNTH),
        "tiers": [{"min": 1, "max": None, "pct": 10}],
    }
    js = _run_node(payload)
    assert js[0]["setupAfterCents"] == 4  # 5 - half_up(0.5) = 5 - 1
    # Python agrees on the identical inputs (same single-tier table).
    synth = ServiceCatalog(
        services=_SYNTH.services,
        bundles={},
        discount_tiers=(DiscountTier(1, None, 10),),
    )
    assert synth.quote_services(["p5"]).setup_after_cents == 4
