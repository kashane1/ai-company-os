"""Cents-only Etsy launch economics and approval gates.

This module models the cash contribution of one order.  It deliberately does
not infer a product or fulfillment cost: an unknown cost blocks approval.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

ETSY_TRANSACTION_FEE_BPS = 650
PAYMENT_PROCESSING_BPS = 300
PAYMENT_PROCESSING_FIXED_CENTS = 25
LISTING_ALLOCATION_CENTS = 20
EXPECTED_OFFSITE_ADS_BPS = 0
OFFSITE_ADS_STRESS_BPS = 1500
MIN_EXPECTED_MARGIN_BPS = 3000


@dataclass(frozen=True)
class EconomicsAssumptions:
    """Known order inputs, expressed only in integer US cents or basis points."""

    sku: str
    item_price_cents: int
    shipping_charged_cents: int
    product_cost_cents: int | None
    fulfillment_shipping_cents: int | None
    reserve_bps: int

    def __post_init__(self) -> None:
        if not self.sku.strip():
            raise ValueError("sku must not be blank")
        for name, value in (
            ("item_price_cents", self.item_price_cents),
            ("shipping_charged_cents", self.shipping_charged_cents),
            ("reserve_bps", self.reserve_bps),
        ):
            if value < 0:
                raise ValueError(f"{name} must not be negative")
        for name, value in (
            ("product_cost_cents", self.product_cost_cents),
            ("fulfillment_shipping_cents", self.fulfillment_shipping_cents),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{name} must not be negative")


@dataclass(frozen=True)
class EconomicsResult:
    """One deterministic scenario; amounts are integer cents and never floats."""

    sku: str
    status: str
    offsite_ads_bps: int
    order_revenue_cents: int
    product_cost_cents: int | None
    fulfillment_shipping_cents: int | None
    transaction_fee_cents: int | None
    payment_processing_fee_cents: int | None
    listing_allocation_cents: int | None
    ad_fee_cents: int | None
    reserve_cents: int | None
    contribution_cents: int | None
    margin_bps: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LaunchEvaluation:
    """Expected and adverse-ad scenario, plus the policy gate result."""

    status: str
    expected: EconomicsResult
    offsite_ads_stress: EconomicsResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "expected": self.expected.to_dict(),
            "offsite_ads_stress": self.offsite_ads_stress.to_dict(),
        }


def _rounded_percent(cents: int, basis_points: int) -> int:
    return int(
        (Decimal(cents) * Decimal(basis_points) / Decimal(10_000)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def calculate_contribution(
    assumptions: EconomicsAssumptions, *, offsite_ads_bps: int
) -> EconomicsResult:
    """Calculate a scenario, returning a block instead of inventing missing costs."""

    if not 0 <= offsite_ads_bps <= 10_000:
        raise ValueError("offsite_ads_bps must be between 0 and 10000")

    order_revenue_cents = assumptions.item_price_cents + assumptions.shipping_charged_cents
    if (
        assumptions.product_cost_cents is None
        or assumptions.fulfillment_shipping_cents is None
    ):
        return EconomicsResult(
            sku=assumptions.sku,
            status="blocked_missing_cost",
            offsite_ads_bps=offsite_ads_bps,
            order_revenue_cents=order_revenue_cents,
            product_cost_cents=assumptions.product_cost_cents,
            fulfillment_shipping_cents=assumptions.fulfillment_shipping_cents,
            transaction_fee_cents=None,
            payment_processing_fee_cents=None,
            listing_allocation_cents=None,
            ad_fee_cents=None,
            reserve_cents=None,
            contribution_cents=None,
            margin_bps=None,
        )

    transaction_fee_cents = _rounded_percent(order_revenue_cents, ETSY_TRANSACTION_FEE_BPS)
    payment_processing_fee_cents = (
        _rounded_percent(order_revenue_cents, PAYMENT_PROCESSING_BPS)
        + PAYMENT_PROCESSING_FIXED_CENTS
    )
    ad_fee_cents = _rounded_percent(order_revenue_cents, offsite_ads_bps)
    reserve_cents = _rounded_percent(order_revenue_cents, assumptions.reserve_bps)
    contribution_cents = (
        order_revenue_cents
        - assumptions.product_cost_cents
        - assumptions.fulfillment_shipping_cents
        - transaction_fee_cents
        - payment_processing_fee_cents
        - LISTING_ALLOCATION_CENTS
        - ad_fee_cents
        - reserve_cents
    )
    # Avoid a float division for the margin.
    margin_bps = int(
        (Decimal(contribution_cents) * Decimal(10_000) / Decimal(order_revenue_cents)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    ) if order_revenue_cents else 0
    return EconomicsResult(
        sku=assumptions.sku,
        status="calculated",
        offsite_ads_bps=offsite_ads_bps,
        order_revenue_cents=order_revenue_cents,
        product_cost_cents=assumptions.product_cost_cents,
        fulfillment_shipping_cents=assumptions.fulfillment_shipping_cents,
        transaction_fee_cents=transaction_fee_cents,
        payment_processing_fee_cents=payment_processing_fee_cents,
        listing_allocation_cents=LISTING_ALLOCATION_CENTS,
        ad_fee_cents=ad_fee_cents,
        reserve_cents=reserve_cents,
        contribution_cents=contribution_cents,
        margin_bps=margin_bps,
    )


def evaluate_launch(assumptions: EconomicsAssumptions) -> LaunchEvaluation:
    """Apply the HomeFromWorking launch gate to expected and 15% ad scenarios."""

    expected = calculate_contribution(assumptions, offsite_ads_bps=EXPECTED_OFFSITE_ADS_BPS)
    stress = calculate_contribution(assumptions, offsite_ads_bps=OFFSITE_ADS_STRESS_BPS)
    if expected.status == "blocked_missing_cost" or stress.status == "blocked_missing_cost":
        status = "blocked_missing_cost"
    elif expected.margin_bps is None or expected.margin_bps < MIN_EXPECTED_MARGIN_BPS:
        status = "blocked_margin_floor"
    elif stress.contribution_cents is None or stress.contribution_cents <= 0:
        status = "blocked_offsite_ads_contribution"
    else:
        status = "approved"
    return LaunchEvaluation(status=status, expected=expected, offsite_ads_stress=stress)
