"""Tests for the inline (catalog-priced) checkout path — agent/CLI parity.

``create_inline_checkout`` is the Python twin of the web ``create-checkout``
function: it prices from the catalog (no STRIPE_PRICE_MAP), builds inline
``price_data`` line items, and branches subscription/payment mode. These tests use
a fake provider so there's no network / no ``stripe`` import.
"""

from __future__ import annotations

import pytest

from packages.agency.payments import (
    CheckoutRequest,
    CheckoutSession,
    PaymentInitiationError,
    create_inline_checkout,
)


class FakeProvider:
    def __init__(self) -> None:
        self.request: CheckoutRequest | None = None

    def create_subscription_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        raise AssertionError("inline path must use create_checkout")

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        self.request = request
        return CheckoutSession(
            url="https://stripe/x", session_id="cs_1", expires_at=request.expires_at
        )


def _setups(req: CheckoutRequest) -> list[int]:
    return [
        li["price_data"]["unit_amount"]
        for li in req.line_items
        if "recurring" not in li["price_data"]
    ]


def _monthlies(req: CheckoutRequest) -> list[int]:
    return [
        li["price_data"]["unit_amount"]
        for li in req.line_items
        if "recurring" in li["price_data"]
    ]


def test_inline_bundle_uses_promo_and_subscription_mode() -> None:
    p = FakeProvider()
    create_inline_checkout("joes-site", provider=p, bundle="package_c", mode="test")
    r = p.request
    assert r is not None
    assert r.mode == "subscription"
    assert r.session_metadata["bundle"] == "package_c"
    assert r.session_metadata["source"] == "agent-cli"
    assert r.subscription_metadata["bundle"] == "package_c"  # rides renewals too
    assert _setups(r) == [180000]  # curated promo
    assert _monthlies(r) == [55000]  # monthly_promo ($550), below the $560 component sum


def test_inline_custom_uses_tier_and_marks_custom() -> None:
    p = FakeProvider()
    create_inline_checkout("joes-site", provider=p, service_ids=["website", "hosting", "gbp"])
    r = p.request
    assert r is not None
    assert r.mode == "subscription"
    assert r.session_metadata["bundle"] == "custom"
    assert r.session_metadata["service_ids"] == "website,hosting,gbp"
    # (500 + 0 + 120) = 620 gross; 3 services → 10% → 558; hosting monthly 50.
    assert _setups(r) == [55800]
    assert _monthlies(r) == [5000]


def test_inline_setup_only_uses_payment_mode() -> None:
    p = FakeProvider()
    create_inline_checkout("x", provider=p, service_ids=["website", "gbp"])
    r = p.request
    assert r is not None
    assert r.mode == "payment"
    assert _monthlies(r) == []  # no recurring line
    assert _setups(r) == [62000]  # 620, 2 services → 0% discount


def test_inline_rejects_invalid_selection() -> None:
    with pytest.raises(PaymentInitiationError):
        create_inline_checkout(
            "x", provider=FakeProvider(), service_ids=["booking_connect", "booking_setup"]
        )


def test_inline_requires_exactly_one_selector() -> None:
    with pytest.raises(PaymentInitiationError):
        create_inline_checkout("x", provider=FakeProvider())
    with pytest.raises(PaymentInitiationError):
        create_inline_checkout(
            "x", provider=FakeProvider(), bundle="package_a", service_ids=["website"]
        )


def test_inline_unknown_bundle_raises() -> None:
    with pytest.raises(PaymentInitiationError):
        create_inline_checkout("x", provider=FakeProvider(), bundle="package_z")
