"""Tests for self-serve order → client promotion (buy-now reconciliation glue)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.catalog import default_catalog
from packages.agency.promotion import PromotionError, promote_order_to_client
from packages.agency.templates import render_offer


def _promote(tmp_path: Path, **over):
    kwargs = dict(
        product_id="joes-plumbing-ab12cd34",
        business_name="Joe's Plumbing",
        service_ids=["website", "hosting", "gbp"],
        registry_path=tmp_path / "products.json",
        docs_root_parent=tmp_path / "docs",
    )
    kwargs.update(over)
    return promote_order_to_client(**kwargs)


def test_promote_order_creates_registry_and_workspace(tmp_path: Path) -> None:
    rec = _promote(tmp_path)
    assert rec["id"] == "joes-plumbing-ab12cd34"
    assert rec["type"] == "client-site"
    assert rec["client"]["services"] == ["website", "hosting", "gbp"]
    assert rec["client"]["from_order"] == "joes-plumbing-ab12cd34"
    assert rec["client"]["billing_status"] == "trial"
    assert rec["client"]["bundle"] == "custom"
    # OFFER.md scaffolded for the custom set
    offer = (tmp_path / "docs" / rec["id"] / "OFFER.md").read_text(encoding="utf-8")
    assert "Custom bundle" in offer


def test_promote_order_is_idempotent(tmp_path: Path) -> None:
    import json

    first = _promote(tmp_path)
    again = _promote(tmp_path)
    assert again["id"] == first["id"]
    registry = json.loads((tmp_path / "products.json").read_text(encoding="utf-8"))
    ids = [r["id"] for r in registry if r["id"] == "joes-plumbing-ab12cd34"]
    assert len(ids) == 1


def test_promote_order_refuses_service_change(tmp_path: Path) -> None:
    _promote(tmp_path)
    with pytest.raises(PromotionError):
        _promote(tmp_path, service_ids=["website"])


def test_promote_order_unknown_service_raises(tmp_path: Path) -> None:
    with pytest.raises(PromotionError):
        _promote(tmp_path, service_ids=["website", "ghost"])


def test_promote_preset_order_uses_promo_offer(tmp_path: Path) -> None:
    catalog = default_catalog()
    ids = catalog.bundles["package_a"].service_ids
    rec = _promote(
        tmp_path,
        product_id="acme-xy",
        business_name="Acme",
        service_ids=list(ids),
        bundle="package_a",
    )
    offer = (tmp_path / "docs" / rec["id"] / "OFFER.md").read_text(encoding="utf-8")
    assert "$599 setup" in offer  # curated promo, not the tier price


def test_render_offer_custom_service_ids() -> None:
    catalog = default_catalog()
    md = render_offer(
        catalog, client_name="X", service_ids=["website", "gbp", "business_email"]
    )
    assert "Custom bundle" in md
    assert "Professional Website" in md


def test_render_offer_requires_one_selector() -> None:
    with pytest.raises(ValueError):
        render_offer(default_catalog(), client_name="X")


def test_process_inbound_order_promotes_from_blob(tmp_path: Path) -> None:
    import json

    from packages.agency.order_fulfillment import process_inbound_order

    inbound = tmp_path / "inbound-orders"
    inbound.mkdir()
    order = {
        "product_id": "diner-co-77",
        "business": "Diner Co",
        "service_ids": ["website", "hosting", "gbp", "business_email"],
        "bundle": "package_a",
        "mode": "test",
    }
    (inbound / "diner-co-77.json").write_text(json.dumps(order), encoding="utf-8")

    rec = process_inbound_order(
        "diner-co-77",
        inbound_root=inbound,
        registry_path=tmp_path / "products.json",
        docs_root_parent=tmp_path / "docs",
    )
    assert rec["id"] == "diner-co-77"
    assert rec["client"]["from_order"] == "diner-co-77"
    assert rec["client"]["bundle"] == "package_a"


def test_process_inbound_order_missing_file_raises(tmp_path: Path) -> None:
    from packages.agency.order_fulfillment import process_inbound_order

    with pytest.raises(FileNotFoundError):
        process_inbound_order("nope", inbound_root=tmp_path)
