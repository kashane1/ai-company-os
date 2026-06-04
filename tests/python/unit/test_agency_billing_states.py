"""Tests for G1 billing hardening — dispute/refund states, B9, ordering, mode,
dead-letter, and write-once acceptance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.agency.billing import (
    BillingDeadLetterError,
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
                        "services": ["website"],
                        "billing_status": "trial",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )


def _event(event_id, event_type, *, created=2000, livemode=False, obj=None) -> dict:
    base_obj = {
        "id": "in_1",
        "customer": "cus_1",
        "subscription": "sub_1",
        "metadata": {"product_id": "joes-plumbing-site", "bundle": "package_c"},
    }
    return {
        "id": event_id,
        "type": event_type,
        "created": created,
        "livemode": livemode,
        "data": {"object": {**base_obj, **(obj or {})}},
    }


def _setup(tmp_path):
    registry = tmp_path / "products.json"
    billing_root = tmp_path / "billing"
    _registry(registry)
    return registry, billing_root


def _reconcile(event, registry, billing_root):
    return reconcile_stripe_event(event, billing_root=billing_root, registry_path=registry)


def test_subscription_created_does_not_activate(tmp_path: Path) -> None:
    registry, billing_root = _setup(tmp_path)
    ledger = _reconcile(_event("e1", "customer.subscription.created"), registry, billing_root)
    assert ledger.billing_status == "trial"  # [B9] created != paid


def test_dispute_created_marks_disputed(tmp_path: Path) -> None:
    registry, billing_root = _setup(tmp_path)
    _reconcile(_event("e1", "invoice.paid", created=1000), registry, billing_root)
    # Dispute object carries no subscription metadata → resolved by customer id.
    dispute = _event(
        "e2", "charge.dispute.created", created=2000,
        obj={"id": "dp_1", "metadata": {}, "status": "needs_response"},
    )
    ledger = _reconcile(dispute, registry, billing_root)
    assert ledger.billing_status == "disputed"
    assert json.loads(registry.read_text())[0]["client"]["billing_status"] == "disputed"


def test_full_refund_marks_refunded_partial_does_not(tmp_path: Path) -> None:
    registry, billing_root = _setup(tmp_path)
    _reconcile(_event("e1", "invoice.paid", created=1000), registry, billing_root)

    partial = _event("e2", "charge.refunded", created=2000, obj={"metadata": {}, "refunded": False})
    assert _reconcile(partial, registry, billing_root).billing_status == "active"

    full = _event("e3", "charge.refunded", created=3000, obj={"metadata": {}, "refunded": True})
    assert _reconcile(full, registry, billing_root).billing_status == "refunded"


def test_late_event_does_not_resurrect_cancelled(tmp_path: Path) -> None:
    registry, billing_root = _setup(tmp_path)
    _reconcile(_event("e1", "invoice.paid", created=2000), registry, billing_root)
    _reconcile(_event("e2", "customer.subscription.deleted", created=3000), registry, billing_root)
    # A late (older) invoice.paid must NOT flip it back to active.
    late = _reconcile(_event("e3", "invoice.paid", created=1000), registry, billing_root)
    assert late.billing_status == "cancelled"


def test_cross_mode_event_is_rejected(tmp_path: Path) -> None:
    registry, billing_root = _setup(tmp_path)
    _reconcile(_event("e1", "invoice.paid", livemode=False), registry, billing_root)
    with pytest.raises(BillingReconciliationError, match="mode"):
        _reconcile(_event("e2", "invoice.paid", livemode=True), registry, billing_root)


def test_unknown_product_dead_letters(tmp_path: Path) -> None:
    registry, billing_root = _setup(tmp_path)
    ghost = _event("e1", "invoice.paid", obj={"metadata": {"product_id": "ghost", "bundle": "x"}})
    with pytest.raises(BillingDeadLetterError):
        _reconcile(ghost, registry, billing_root)
    assert (billing_root / "dead-letter" / "e1.json").exists()
    # No orphan live ledger was written.
    assert load_ledger("ghost", billing_root=billing_root) is None


def test_acceptance_stamped_once(tmp_path: Path) -> None:
    registry, billing_root = _setup(tmp_path)
    _reconcile(_event("e1", "invoice.paid", created=1000), registry, billing_root)
    client = json.loads(registry.read_text())[0]["client"]
    assert client["accepted_at"] == "1000"
    assert client["accepted_by"] == "cus_1"

    # A later paid invoice must not rewrite the original acceptance.
    _reconcile(_event("e2", "invoice.paid", created=5000), registry, billing_root)
    client = json.loads(registry.read_text())[0]["client"]
    assert client["accepted_at"] == "1000"
