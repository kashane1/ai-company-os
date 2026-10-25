#!/usr/bin/env python3
"""Validate and render HomeFromWorking's read-only launch economics policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.home_from_working.economics import (  # noqa: E402
    EXPECTED_OFFSITE_ADS_BPS,
    MIN_EXPECTED_MARGIN_BPS,
    OFFSITE_ADS_STRESS_BPS,
    EconomicsAssumptions,
    evaluate_launch,
)

DEFAULT_POLICY = Path("state/home-from-working/operations/launch-policy.json")


def load_policy(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        policy = json.load(handle)
    if not isinstance(policy, dict):
        raise ValueError("launch policy must be a JSON object")
    return policy


def validate_policy(policy: dict[str, Any]) -> list[str]:
    """Return policy violations; this command intentionally makes no account changes."""

    errors: list[str] = []
    shipping = policy.get("shipping", {})
    offsite_ads = policy.get("offsite_ads", {})
    reserve = policy.get("reserve", {})
    approval_rules = policy.get("approval_rules", {})
    if shipping.get("buyer_paid_us_shipping_cents") != 495:
        errors.append("buyer_paid_us_shipping_cents must be 495 for the approved baseline")
    if shipping.get("free_shipping_guarantee_enabled") is not False:
        errors.append("free_shipping_guarantee_enabled must be false for the approved baseline")
    if offsite_ads.get("operational_status") != "disabled":
        errors.append("offsite_ads.operational_status must be disabled")
    if offsite_ads.get("expected_fee_bps") != EXPECTED_OFFSITE_ADS_BPS:
        errors.append("expected Offsite Ads fee must be 0 bps")
    if offsite_ads.get("stress_fee_bps") != OFFSITE_ADS_STRESS_BPS:
        errors.append("Offsite Ads stress fee must be 1500 bps")
    reserve_bps = reserve.get("reserve_bps")
    if not isinstance(reserve_bps, int) or not 0 <= reserve_bps <= 500:
        errors.append("reserve_bps must be an integer from 0 through 500")
    if approval_rules.get("minimum_expected_margin_bps") != MIN_EXPECTED_MARGIN_BPS:
        errors.append("minimum_expected_margin_bps must be 3000")
    if approval_rules.get("missing_cost_status") != "blocked_missing_cost":
        errors.append("missing_cost_status must be blocked_missing_cost")
    if not policy.get("current_single_shirt_variants"):
        errors.append("current_single_shirt_variants must not be empty")
    return errors


def evaluate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    errors = validate_policy(policy)
    reserve_bps = policy.get("reserve", {}).get("reserve_bps", 0)
    shipping_cents = policy.get("shipping", {}).get("buyer_paid_us_shipping_cents", 0)
    evaluations = []
    for variant in policy.get("current_single_shirt_variants", []):
        assumptions = EconomicsAssumptions(
            sku=str(variant["sku"]),
            item_price_cents=int(variant["item_price_cents"]),
            shipping_charged_cents=int(shipping_cents),
            product_cost_cents=variant.get("product_cost_cents"),
            fulfillment_shipping_cents=variant.get("fulfillment_shipping_cents"),
            reserve_bps=int(reserve_bps),
        )
        evaluation = evaluate_launch(assumptions).to_dict()
        evaluations.append({"sizes": variant.get("sizes", []), **evaluation})
    approved = not errors and all(item["status"] == "approved" for item in evaluations)
    return {
        "status": "approved" if approved else "blocked",
        "account_mutations": 0,
        "policy_errors": errors,
        "evaluations": evaluations,
    }


def format_cents(cents: int | None) -> str:
    if cents is None:
        return "unknown"
    return f"${cents // 100}.{cents % 100:02d}"


def format_bps(bps: int | None) -> str:
    if bps is None:
        return "unknown"
    return f"{bps // 100}.{bps % 100:02d}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--json", action="store_true", help="render deterministic JSON")
    args = parser.parse_args()
    try:
        result = evaluate_policy(load_policy(args.policy))
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(f"launch policy: {result['status']} (account mutations: 0)")
        for item in result["evaluations"]:
            expected = item["expected"]
            stress = item["offsite_ads_stress"]
            print(f"- {expected['sku']}: {item['status']}; expected "
                  f"{format_cents(expected['contribution_cents'])} "
                  f"({format_bps(expected['margin_bps'])}), 15% ad stress "
                  f"{format_cents(stress['contribution_cents'])}")
        for error in result["policy_errors"]:
            print(f"policy error: {error}")
    return 0 if result["status"] == "approved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
