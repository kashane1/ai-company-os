"""Tests for the OFFER.md payment-link injection (G1/G3)."""

from __future__ import annotations

from packages.agency.catalog import default_catalog
from packages.agency.templates import render_offer


def test_offer_without_payment_link_has_no_pay_section() -> None:
    out = render_offer(default_catalog(), "package_c", client_name="Joe's Plumbing")
    assert "## Pay & start" not in out
    assert "## Included services" in out  # unchanged base render


def test_offer_with_payment_link_renders_pay_section() -> None:
    out = render_offer(
        default_catalog(),
        "package_c",
        client_name="Joe's Plumbing",
        payment_link="https://checkout.stripe.com/c/pay/cs_test_123",
        payment_expires_at="2026-06-05T00:00:00Z",
    )
    assert "## Pay & start" in out
    assert "https://checkout.stripe.com/c/pay/cs_test_123" in out
    assert "link expires 2026-06-05T00:00:00Z" in out
