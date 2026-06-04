import json
from pathlib import Path

import pytest

from packages.agency.billing import (
    BillingReconciliationError,
    load_ledger,
    reconcile_stripe_event,
)


def _registry(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "id": "joes-plumbing-site",
                    "name": "Joe's Plumbing",
                    "slug": "joes-plumbing",
                    "type": "client-site",
                    "platform": "web",
                    "source_path": "products/joes-plumbing-site",
                    "docs_root": "docs/products/joes-plumbing-site",
                    "client": {
                        "bundle": "package_c",
                        "services": ["website", "google_ads"],
                        "billing_status": "trial",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )


def _event(event_id: str = "evt_1", event_type: str = "invoice.paid") -> dict[str, object]:
    return {
        "id": event_id,
        "type": event_type,
        "created": "2026-06-03T00:00:00Z",
        "livemode": False,
        "data": {
            "object": {
                "id": "in_1",
                "customer": "cus_1",
                "subscription": "sub_1",
                "metadata": {
                    "product_id": "joes-plumbing-site",
                    "bundle": "package_c",
                    "monthly_price_id": "price_monthly",
                },
            }
        },
    }


def test_reconcile_stripe_event_updates_ledger_and_registry(tmp_path: Path) -> None:
    registry = tmp_path / "products.json"
    billing_root = tmp_path / "billing"
    _registry(registry)

    ledger = reconcile_stripe_event(
        _event(),
        billing_root=billing_root,
        registry_path=registry,
    )

    assert ledger.product_id == "joes-plumbing-site"
    assert ledger.billing_status == "active"
    assert ledger.subscription_id == "sub_1"
    assert ledger.processed_event_ids == ["evt_1"]
    saved = load_ledger("joes-plumbing-site", billing_root=billing_root)
    assert saved is not None
    assert saved.customer_id == "cus_1"
    updated = json.loads(registry.read_text(encoding="utf-8"))
    assert updated[0]["client"]["billing_status"] == "active"


def test_reconcile_stripe_event_is_idempotent(tmp_path: Path) -> None:
    registry = tmp_path / "products.json"
    billing_root = tmp_path / "billing"
    _registry(registry)

    reconcile_stripe_event(_event(), billing_root=billing_root, registry_path=registry)
    ledger = reconcile_stripe_event(_event(), billing_root=billing_root, registry_path=registry)

    assert ledger.processed_event_ids == ["evt_1"]


def test_reconcile_payment_failed_marks_past_due(tmp_path: Path) -> None:
    registry = tmp_path / "products.json"
    billing_root = tmp_path / "billing"
    _registry(registry)

    ledger = reconcile_stripe_event(
        _event(event_id="evt_2", event_type="invoice.payment_failed"),
        billing_root=billing_root,
        registry_path=registry,
    )

    assert ledger.billing_status == "past_due"
    updated = json.loads(registry.read_text(encoding="utf-8"))
    assert updated[0]["client"]["billing_status"] == "past_due"


def test_reconcile_requires_product_metadata(tmp_path: Path) -> None:
    event = _event()
    event["data"]["object"]["metadata"] = {}

    with pytest.raises(BillingReconciliationError):
        reconcile_stripe_event(
            event,
            billing_root=tmp_path / "billing",
            registry_path=tmp_path / "products.json",
        )
