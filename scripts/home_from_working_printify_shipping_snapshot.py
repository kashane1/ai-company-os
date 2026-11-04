#!/usr/bin/env python3
"""Capture exact, read-only U.S. Printify shipping evidence for the shirt template."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.config.secrets import require_secret  # noqa: E402
from packages.pod.runner import (  # noqa: E402
    TEMPLATE_ID,
    DraftError,
    PrintifyClient,
    save_json,
)
from scripts.home_from_working_printify_snapshot import (  # noqa: E402
    EVIDENCE_ROOT,
    ensure_output_writable,
)


def _positive_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DraftError(f"Printify {label} must be a positive integer.")
    return value


def _usd_amount(value: object, *, label: str) -> int:
    if not isinstance(value, dict):
        raise DraftError(f"Printify {label} must be a USD cost object.")
    cost = value.get("amount")
    currency = value.get("currency")
    if (
        isinstance(cost, bool)
        or not isinstance(cost, int)
        or cost < 0
        or currency != "USD"
    ):
        raise DraftError(f"Printify {label} must contain a non-negative USD cost.")
    return cost


def build_shipping_snapshot(
    client: PrintifyClient, *, product_id: str, observed_at: str
) -> dict[str, Any]:
    """Join one exact product's enabled variants to current catalog shipping."""
    product = client.get_product(product_id)
    if not isinstance(product, dict) or product.get("id") != product_id:
        raise DraftError("Printify source product response did not match the requested ID.")
    blueprint_id = _positive_int(product.get("blueprint_id"), label="blueprint ID")
    provider_id = _positive_int(
        product.get("print_provider_id"), label="print provider ID"
    )
    variants = product.get("variants")
    if not isinstance(variants, list) or any(
        not isinstance(variant, dict) for variant in variants
    ):
        raise DraftError("Printify source product variants are invalid.")

    enabled_ids: set[int] = set()
    for variant in variants:
        if variant.get("is_enabled") is not True:
            continue
        variant_id = _positive_int(variant.get("id"), label="enabled variant ID")
        if variant_id in enabled_ids:
            raise DraftError(f"Duplicate enabled Printify variant ID: {variant_id}")
        enabled_ids.add(variant_id)
    if not enabled_ids:
        raise DraftError("Printify source product has no enabled variants.")

    shipping = client.get_catalog_standard_shipping(blueprint_id, provider_id)
    entries = shipping.get("data") if isinstance(shipping, dict) else None
    if not isinstance(entries, list) or any(
        not isinstance(entry, dict) for entry in entries
    ):
        raise DraftError("Printify standard shipping response has invalid data.")

    rates_by_variant: dict[int, set[tuple[int, int]]] = {
        variant_id: set() for variant_id in enabled_ids
    }
    row_count_by_variant = {variant_id: 0 for variant_id in enabled_ids}
    for entry in entries:
        attributes = entry.get("attributes")
        if not isinstance(attributes, dict):
            raise DraftError("Printify standard shipping entry is invalid.")
        country = attributes.get("country")
        if (
            attributes.get("shippingType") != "standard"
            or not isinstance(country, dict)
            or not isinstance(country.get("code"), str)
        ):
            raise DraftError("Printify standard shipping attributes are invalid.")
        variant_id = _positive_int(
            attributes.get("variantId"), label="shipping variant ID"
        )
        if country["code"] != "US" or variant_id not in enabled_ids:
            continue
        shipping_cost = attributes.get("shippingCost")
        if not isinstance(shipping_cost, dict):
            raise DraftError("Printify standard shipping cost is invalid.")
        first_item = _usd_amount(
            shipping_cost.get("firstItem"), label="first-item shipping"
        )
        additional_item = _usd_amount(
            shipping_cost.get("additionalItems"),
            label="additional-item shipping",
        )
        rates_by_variant[variant_id].add((first_item, additional_item))
        row_count_by_variant[variant_id] += 1

    if any(len(rates) > 1 for rates in rates_by_variant.values()):
        raise DraftError(
            "Enabled Printify variants have conflicting U.S. standard shipping rates."
        )
    if any(not rates for rates in rates_by_variant.values()):
        raise DraftError(
            "Printify U.S. shipping profiles must cover every enabled variant."
        )

    grouped_variant_ids: dict[tuple[int, int], list[int]] = {}
    for variant_id, rates in rates_by_variant.items():
        rate = next(iter(rates))
        grouped_variant_ids.setdefault(rate, []).append(variant_id)
    groups = [
        {
            "enabled_variant_ids": sorted(variant_ids),
            "first_item_cost_cents": first_item,
            "additional_item_cost_cents": additional_item,
            "currency": "USD",
        }
        for (first_item, additional_item), variant_ids in grouped_variant_ids.items()
    ]

    groups.sort(
        key=lambda group: (
            group["first_item_cost_cents"],
            group["additional_item_cost_cents"],
            group["enabled_variant_ids"],
        )
    )
    first_item_costs = sorted(
        {group["first_item_cost_cents"] for group in groups}
    )
    additional_item_costs = sorted(
        {group["additional_item_cost_cents"] for group in groups}
    )
    return {
        "schema_version": 1,
        "observed_at": observed_at,
        "mode": "read_only",
        "external_account_writes": 0,
        "source_product": {
            "id": product_id,
            "blueprint_id": blueprint_id,
            "print_provider_id": provider_id,
            "enabled_variant_count": len(enabled_ids),
        },
        "us_standard": {
            "covered_enabled_variant_ids": sorted(enabled_ids),
            "first_item_cost_cents": first_item_costs,
            "additional_item_cost_cents": additional_item_costs,
            "maximum_first_item_cost_cents": max(first_item_costs),
            "maximum_additional_item_cost_cents": max(additional_item_costs),
            "equivalent_duplicate_rows_collapsed": sum(
                max(0, count - 1) for count in row_count_by_variant.values()
            ),
            "groups": groups,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-id", default=TEMPLATE_ID)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--observed-at")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    observed_at = (
        args.observed_at
        or datetime.now().astimezone().replace(microsecond=0).isoformat()
    )
    timestamp = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    output = args.output or (
        EVIDENCE_ROOT
        / timestamp.date().isoformat()
        / "printify-shipping-rates.json"
    )
    ensure_output_writable(output, overwrite=args.overwrite)

    client = PrintifyClient(require_secret("PRINTIFY_API_TOKEN", source="keychain"))
    try:
        snapshot = build_shipping_snapshot(
            client,
            product_id=args.product_id,
            observed_at=observed_at,
        )
    finally:
        client.close()
    save_json(output, snapshot)
    print(f"saved verified Printify shipping rates to {output} (account writes: 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
