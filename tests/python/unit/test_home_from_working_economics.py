"""Launch economics are deterministic and never approve guessed costs."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.home_from_working.economics import (
    EconomicsAssumptions,
    evaluate_launch,
    calculate_contribution,
)
from scripts.home_from_working_launch import evaluate_policy, load_policy


LAUNCH_POLICY = Path("state/home-from-working/operations/launch-policy.json")
# Runtime state under state/ is git-ignored, so this check runs only on the operator Mac.
requires_local_state = pytest.mark.skipif(
    not LAUNCH_POLICY.exists(), reason="requires local HomeFromWorking runtime state"
)


def shirt(*, product_cost_cents: int | None = 740) -> EconomicsAssumptions:
    return EconomicsAssumptions(
        sku="shirt-s-xl",
        item_price_cents=1799,
        shipping_charged_cents=495,
        product_cost_cents=product_cost_cents,
        fulfillment_shipping_cents=495,
        reserve_bps=200,
    )


def test_contribution_uses_all_etsy_fee_components_in_cents() -> None:
    result = calculate_contribution(shirt(), offsite_ads_bps=0)

    assert result.order_revenue_cents == 2294
    assert result.transaction_fee_cents == 149  # 6.5% of item plus buyer-paid shipping
    assert result.payment_processing_fee_cents == 94  # 3%, rounded, plus $0.25
    assert result.listing_allocation_cents == 20
    assert result.reserve_cents == 46  # 2% of order revenue
    assert result.ad_fee_cents == 0
    assert result.contribution_cents == 750
    assert result.margin_bps == 3269


def test_offsite_ads_zero_and_fifteen_percent_scenarios() -> None:
    expected = calculate_contribution(shirt(), offsite_ads_bps=0)
    stressed = calculate_contribution(shirt(), offsite_ads_bps=1500)

    assert expected.ad_fee_cents == 0
    assert stressed.ad_fee_cents == 344
    assert stressed.contribution_cents == 406
    assert stressed.contribution_cents == expected.contribution_cents - 344


def test_launch_approval_needs_thirty_percent_expected_margin_and_positive_stress_case() -> None:
    approved = evaluate_launch(shirt())
    assert approved.status == "approved"
    assert approved.expected.margin_bps >= 3000
    assert approved.offsite_ads_stress.contribution_cents > 0

    low_margin = evaluate_launch(
        EconomicsAssumptions(
            sku="low-margin",
            item_price_cents=1799,
            shipping_charged_cents=495,
            product_cost_cents=860,
            fulfillment_shipping_cents=495,
            reserve_bps=200,
        )
    )
    assert low_margin.status == "blocked_margin_floor"


def test_missing_actual_cost_is_blocked_never_guessed() -> None:
    result = calculate_contribution(shirt(product_cost_cents=None), offsite_ads_bps=0)
    approval = evaluate_launch(shirt(product_cost_cents=None))

    assert result.status == "blocked_missing_cost"
    assert result.contribution_cents is None
    assert approval.status == "blocked_missing_cost"


def test_current_3xl_live_cost_does_not_clear_thirty_percent_margin_floor() -> None:
    current = EconomicsAssumptions(
        sku="shirt-3xl",
        item_price_cents=2099,
        shipping_charged_cents=495,
        product_cost_cents=987,
        fulfillment_shipping_cents=495,
        reserve_bps=200,
    )

    result = evaluate_launch(current)

    assert result.status == "blocked_margin_floor"
    assert result.expected.contribution_cents == 768
    assert result.expected.margin_bps == 2961
    assert result.offsite_ads_stress.contribution_cents > 0


@requires_local_state
def test_launch_policy_uses_live_printify_size_costs_and_blocks_current_3xl() -> None:
    policy = load_policy(LAUNCH_POLICY)
    costs = {
        variant["sku"]: variant["product_cost_cents"]
        for variant in policy["current_single_shirt_variants"]
    }

    assert costs == {
        "shirt-s-xl": 740,
        "shirt-2xl": 894,
        "shirt-3xl": 987,
        "shirt-4xl-5xl": 1034,
    }
    evaluation = evaluate_policy(policy)
    three_xl = next(
        item for item in evaluation["evaluations"] if item["expected"]["sku"] == "shirt-3xl"
    )
    assert evaluation["status"] == "blocked"
    assert three_xl["status"] == "blocked_margin_floor"
