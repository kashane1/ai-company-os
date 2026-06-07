"""Tests for the agency service catalog (Phase 1)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from packages.agency.catalog import default_catalog, load_catalog
from packages.agency.templates import render_catalog_json
from packages.schemas.offer import (
    BillType,
    Bundle,
    CatalogError,
    DiscountTier,
    Service,
    ServiceCatalog,
    ServiceTier,
    to_cents,
)


def test_bundled_catalog_loads_and_validates() -> None:
    catalog = load_catalog()
    assert "website" in catalog.services
    assert {"package_a", "package_b", "package_c"} <= set(catalog.bundles)


def test_default_catalog_is_cached() -> None:
    assert default_catalog() is default_catalog()


def test_bundles_reference_real_services() -> None:
    catalog = default_catalog()
    known = set(catalog.services)
    for bundle in catalog.bundles.values():
        assert set(bundle.service_ids) <= known, bundle.bundle_id


def test_quote_bundle_applies_promo_and_sums_monthly() -> None:
    catalog = default_catalog()
    quote = catalog.quote_bundle("package_a")
    ids = catalog.bundles["package_a"].service_ids
    gross = sum(to_cents(catalog.services[s].setup_fee) for s in ids)
    monthly = sum(to_cents(catalog.services[s].monthly_fee) for s in ids)
    # Setup gross is the plain sum; monthly is never discounted.
    assert quote.setup_gross_cents == gross
    assert quote.monthly_cents == monthly
    # Package A is sold at its curated promo, cheaper than the tier discount.
    assert quote.pricing_mode == "promo"
    assert quote.setup_after_cents == 59900
    assert quote.savings_cents == gross - 59900
    # Package A is a setup + monthly offer.
    assert quote.setup_after_cents > 0
    assert quote.monthly_cents > 0


def test_packages_escalate_in_scope() -> None:
    catalog = default_catalog()
    a = set(catalog.bundles["package_a"].service_ids)
    b = set(catalog.bundles["package_b"].service_ids)
    c = set(catalog.bundles["package_c"].service_ids)
    assert a < b < c  # strict supersets — each package builds on the last


def test_schema_round_trips() -> None:
    catalog = default_catalog()
    rebuilt = ServiceCatalog.from_dict(catalog.to_dict())
    assert rebuilt.to_dict() == catalog.to_dict()


def test_quote_unknown_bundle_raises() -> None:
    with pytest.raises(CatalogError):
        default_catalog().quote_bundle("package_z")


def test_recurring_service_requires_monthly_fee() -> None:
    bad = Service(
        service_id="x",
        name="X",
        tier=ServiceTier.TIER_2,
        bill_type=BillType.RECURRING,
        monthly_fee=0,
    )
    with pytest.raises(CatalogError):
        bad.validate()


def test_one_time_service_requires_setup_fee() -> None:
    bad = Service(
        service_id="y",
        name="Y",
        tier=ServiceTier.TIER_1,
        bill_type=BillType.ONE_TIME,
        setup_fee=0,
    )
    with pytest.raises(CatalogError):
        bad.validate()


def test_catalog_rejects_dangling_bundle_reference() -> None:
    catalog = ServiceCatalog(
        services={
            "real": Service(
                service_id="real",
                name="Real",
                tier=ServiceTier.TIER_1,
                bill_type=BillType.ONE_TIME,
                setup_fee=100,
            )
        },
        bundles={"b": Bundle(bundle_id="b", name="B", service_ids=["real", "ghost"])},
    )
    with pytest.raises(CatalogError):
        catalog.validate()


def test_load_catalog_from_custom_path(tmp_path: Path) -> None:
    yaml_text = textwrap.dedent(
        """
        services:
          - service_id: solo
            name: Solo
            tier: tier_1
            bill_type: one_time
            setup_fee: 250
        bundles:
          - bundle_id: only
            name: Only
            service_ids: [solo]
        """
    )
    path = tmp_path / "catalog.yaml"
    path.write_text(yaml_text)
    catalog = load_catalog(path)
    assert catalog.quote_bundle("only").setup_after_cents == 25000


# --- discount engine -------------------------------------------------------


def _svc(sid: str, setup: float = 0.0, monthly: float = 0.0) -> Service:
    bill = BillType.RECURRING if monthly else BillType.ONE_TIME
    return Service(sid, sid.title(), ServiceTier.TIER_1, bill, setup, monthly)


def _catalog(services, *, tiers=((1, None, 10),), bundles=None) -> ServiceCatalog:
    return ServiceCatalog(
        services={s.service_id: s for s in services},
        bundles=bundles or {},
        discount_tiers=tuple(
            DiscountTier(mn, mx, pct) for (mn, mx, pct) in tiers
        ),
    )


def test_tier_discount_applies_to_custom_cart() -> None:
    cat = _catalog(
        [_svc("a", setup=300), _svc("b", setup=400), _svc("c", setup=300)],
        tiers=((1, 2, 0), (3, 4, 10), (5, None, 15)),
    )
    q = cat.quote_services(["a", "b", "c"])  # 3 services -> 10%
    assert q.pricing_mode == "tier"
    assert q.tier_pct == 10
    assert q.setup_gross_cents == 100000
    assert q.setup_after_cents == 90000  # 10% off setup
    assert q.savings_cents == 10000


def test_monthly_never_discounted() -> None:
    cat = _catalog(
        [_svc(c, setup=100, monthly=50) for c in "abcde"],
        tiers=((5, None, 15),),
    )
    q = cat.quote_services(list("abcde"))  # 5 services -> 15% on setup only
    assert q.tier_pct == 15
    assert q.setup_after_cents == 42500  # 500_00 - 15%
    assert q.monthly_cents == 25000  # 5 * 50_00, untouched by the discount


def test_discount_rounds_half_up_not_bankers() -> None:
    # gross 5c, 10% -> 0.5c; half-up rounds to 1c (banker's would give 0).
    cat = _catalog([_svc("x", setup=0.05)], tiers=((1, None, 10),))
    q = cat.quote_services(["x"])
    assert q.setup_gross_cents == 5
    assert q.setup_after_cents == 4  # 5 - half_up(0.5) = 5 - 1


def test_promo_exceeding_tier_discount_is_rejected() -> None:
    services = [_svc("a", setup=300), _svc("b", setup=400), _svc("c", setup=300)]
    # 3 svc, 10% tier -> tier-after = 900_00. A promo of 950 (95000c) is worse.
    bundles = {
        "bad": Bundle("bad", "Bad", ["a", "b", "c"], setup_promo=950),
    }
    cat = _catalog(services, tiers=((3, 4, 10),), bundles=bundles)
    with pytest.raises(CatalogError):
        cat.validate()


def test_promo_at_or_below_tier_discount_is_accepted() -> None:
    services = [_svc("a", setup=300), _svc("b", setup=400), _svc("c", setup=300)]
    bundles = {"ok": Bundle("ok", "Ok", ["a", "b", "c"], setup_promo=850)}
    cat = _catalog(services, tiers=((3, 4, 10),), bundles=bundles)
    cat.validate()  # 850 <= 900 tier-after -> fine
    assert cat.quote_bundle("ok").setup_after_cents == 85000


# --- variant groups (exclusive / dependency) -------------------------------


def test_validate_selection_real_booking_family() -> None:
    catalog = default_catalog()
    # two bases from the same exclusive group is invalid
    assert catalog.validate_selection(["booking_connect", "booking_setup"])
    # a modifier without a base is invalid
    assert catalog.validate_selection(["booking_deposits"])
    # one base + a modifier is fine
    assert catalog.validate_selection(["booking_setup", "booking_deposits"]) == []
    # a single base is fine
    assert catalog.validate_selection(["booking_native"]) == []
    # non-booking services are unaffected
    assert catalog.validate_selection(["website", "hosting"]) == []


def test_services_payload_exposes_variant_fields() -> None:
    services = {s["id"]: s for s in render_catalog_json(default_catalog())["services"]}
    assert services["booking_setup"]["exclusive_group"] == "booking_base"
    assert services["booking_deposits"]["requires_group"] == "booking_base"
    assert services["website"]["exclusive_group"] == ""
