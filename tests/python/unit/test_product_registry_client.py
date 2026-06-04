"""Phase 2 — client-site records load through the product registry."""

from __future__ import annotations

import json
from pathlib import Path

from packages.config.products import load_product_configs
from packages.schemas.product import ProductPhase, ProductType


def test_joes_plumbing_client_site_loads() -> None:
    configs = load_product_configs()
    cfg = configs["joes-plumbing-site"]
    assert cfg.type is ProductType.CLIENT_SITE
    assert cfg.platform.value == "web"
    assert cfg.client is not None
    assert cfg.client.bundle == "package_b"
    assert cfg.client.from_prospect == "example-prospect-id"


def test_client_site_without_repo_id(tmp_path: Path) -> None:
    registry = tmp_path / "products.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "id": "acme-site",
                    "name": "Acme Co",
                    "slug": "acme-co",
                    "type": "client-site",
                    "platform": "web",
                    "source_path": "products/acme-site",
                    "docs_root": "docs/products/acme-site",
                    "phase": "mvp-build",
                    "client": {
                        "ownership": "client-owned",
                        "bundle": "package_a",
                        "services": ["website", "hosting"],
                        "from_prospect": "ChIJtest",
                        "billing_status": "active",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    configs = load_product_configs(registry)
    cfg = configs["acme-site"]
    assert cfg.type is ProductType.CLIENT_SITE
    assert cfg.phase is ProductPhase.MVP_BUILD
    assert cfg.repo_id == ""
    assert cfg.client is not None
    assert cfg.client.billing_status.value == "active"
