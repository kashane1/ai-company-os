"""Tests for the agency service catalog (Phase 1)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from packages.agency.catalog import default_catalog, load_catalog
from packages.schemas.offer import (
    BillType,
    Bundle,
    CatalogError,
    Service,
    ServiceCatalog,
    ServiceTier,
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


def test_quote_bundle_sums_setup_and_monthly() -> None:
    catalog = default_catalog()
    quote = catalog.quote_bundle("package_a")
    ids = catalog.bundles["package_a"].service_ids
    expected_setup = sum(catalog.services[s].setup_fee for s in ids)
    expected_monthly = sum(catalog.services[s].monthly_fee for s in ids)
    assert quote.setup_total == round(expected_setup, 2)
    assert quote.monthly_total == round(expected_monthly, 2)
    # Package A is a setup + monthly offer.
    assert quote.setup_total > 0
    assert quote.monthly_total > 0


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
    assert catalog.quote_bundle("only").setup_total == 250
