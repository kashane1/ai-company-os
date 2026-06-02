"""Agency layer Phase 2 — client-site product registry records."""

from __future__ import annotations

import json
from pathlib import Path

from packages.agency.catalog import default_catalog
from packages.config.products import load_product_configs
from packages.schemas.product import (
    BillingStatus,
    ClientOwnership,
    ProductPlatform,
    ProductType,
)


def test_real_registry_loads_client_site_record() -> None:
    configs = load_product_configs()
    client = configs["joes-plumbing-site"]
    assert client.type is ProductType.CLIENT_SITE
    assert client.platform is ProductPlatform.WEB
    assert client.client is not None
    assert client.client.bundle == "package_b"
    assert client.client.ownership is ClientOwnership.CLIENT_OWNED
    assert client.client.billing_status is BillingStatus.TRIAL


def test_client_bundle_resolves_against_catalog() -> None:
    configs = load_product_configs()
    client = configs["joes-plumbing-site"]
    assert client.client is not None
    quote = default_catalog().quote_bundle(client.client.bundle)
    # The record's declared services should match the bundle definition.
    assert set(client.client.services) == {s.service_id for s in quote.services}


def test_existing_products_default_to_product_type() -> None:
    configs = load_product_configs()
    for pid in ("catchbook", "after-plans", "life-clock"):
        assert configs[pid].type is ProductType.PRODUCT
        assert configs[pid].client is None


def test_client_site_can_omit_platform_and_repo_id(tmp_path: Path) -> None:
    registry = tmp_path / "products.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "id": "acme-site",
                    "name": "Acme",
                    "slug": "acme",
                    "type": "client-site",
                    "source_path": "products/acme-site",
                    "docs_root": "docs/products/acme-site",
                    "client": {"bundle": "package_a"},
                }
            ]
        )
    )
    configs = load_product_configs(registry)
    acme = configs["acme-site"]
    assert acme.type is ProductType.CLIENT_SITE
    assert acme.platform is ProductPlatform.WEB  # defaulted
    assert acme.repo_id == ""  # relaxed
    assert acme.client is not None and acme.client.bundle == "package_a"


def test_client_block_round_trips() -> None:
    configs = load_product_configs()
    client = configs["joes-plumbing-site"].client
    assert client is not None
    from packages.schemas.product import ClientConfig

    assert ClientConfig.from_dict(client.to_dict()).to_dict() == client.to_dict()
