"""Tests for Stripe Checkout initiation (G1) — param shaping + live gate."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from packages.agency.payments import (
    CheckoutProvider,
    CheckoutRequest,
    CheckoutSession,
    PaymentInitiationError,
    create_client_checkout,
    resolve_price_entry,
)
from packages.db.approval_store import ApprovalStore
from packages.policies.approvals import PolicyViolation

PRICE_MAP = {"package_c": {"test": {"setup": "price_setup", "monthly": "price_monthly"}}}
FIXED = lambda: datetime(2026, 6, 4, 0, 0, tzinfo=timezone.utc)  # noqa: E731
EPOCH = int(datetime(2026, 6, 4, 0, 0, tzinfo=timezone.utc).timestamp())


class FakeProvider:
    def __init__(self) -> None:
        self.request: CheckoutRequest | None = None

    def create_subscription_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        self.request = request
        return CheckoutSession(
            url="https://checkout.test/cs_1", session_id="cs_1", expires_at=request.expires_at
        )


def test_fake_provider_satisfies_protocol() -> None:
    assert isinstance(FakeProvider(), CheckoutProvider)


def test_checkout_shaping_test_mode() -> None:
    provider = FakeProvider()
    session = create_client_checkout(
        "joes-plumbing-site", "package_c", provider=provider, mode="test",
        price_map=PRICE_MAP, now=FIXED,
    )
    req = provider.request
    assert req is not None and req.mode == "subscription"
    # Two line items: recurring monthly first, one-time setup second.
    assert [li["price"] for li in req.line_items] == ["price_monthly", "price_setup"]
    # Metadata on BOTH session and subscription so invoice.paid carries it.
    meta = {"product_id": "joes-plumbing-site", "bundle": "package_c", "mode": "test"}
    assert req.session_metadata == meta
    assert req.subscription_metadata == meta
    assert req.idempotency_key == "checkout:joes-plumbing-site:package_c:test"
    assert req.expires_at == EPOCH + 24 * 60 * 60
    assert session.url == "https://checkout.test/cs_1"


def test_expiry_is_clamped() -> None:
    provider = FakeProvider()
    create_client_checkout(
        "p", "package_c", provider=provider, mode="test", price_map=PRICE_MAP,
        expires_in_seconds=10**9, now=FIXED,
    )
    assert provider.request.expires_at == EPOCH + 24 * 60 * 60  # capped at 24h


def test_missing_price_entry_raises() -> None:
    with pytest.raises(PaymentInitiationError, match="price-map"):
        create_client_checkout(
            "p", "package_a", provider=FakeProvider(), mode="test", price_map=PRICE_MAP
        )


def test_bad_mode_raises() -> None:
    with pytest.raises(PaymentInitiationError, match="mode"):
        create_client_checkout(
            "p", "package_c", provider=FakeProvider(), mode="prod", price_map=PRICE_MAP
        )


def test_resolve_price_entry_requires_both_ids() -> None:
    with pytest.raises(PaymentInitiationError):
        resolve_price_entry({"package_c": {"test": {"setup": "price_x"}}}, "package_c", "test")


def test_live_mode_without_approval_is_refused(isolated_repo_root) -> None:
    with pytest.raises(PolicyViolation) as exc:
        create_client_checkout(
            "joes-plumbing-site", "package_c", provider=FakeProvider(), mode="live",
            approval_id="missing", store=ApprovalStore(), price_map=PRICE_MAP, now=FIXED,
        )
    assert exc.value.code == "retainer_approval_not_granted"
