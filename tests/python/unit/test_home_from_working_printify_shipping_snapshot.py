from __future__ import annotations

import copy

import pytest

from packages.pod.template import DraftError
from scripts.home_from_working_printify_shipping_snapshot import (
    build_shipping_snapshot,
)


class FakePrintify:
    def get_product(self, product_id):
        return {
            "id": product_id,
            "blueprint_id": 6,
            "print_provider_id": 99,
            "variants": [
                {"id": 10, "is_enabled": True},
                {"id": 11, "is_enabled": True},
                {"id": 12, "is_enabled": False},
            ],
        }

    def get_catalog_standard_shipping(self, blueprint_id, print_provider_id):
        assert (blueprint_id, print_provider_id) == (6, 99)
        return {
            "data": [
                {
                    "type": "variant_shipping_standard_us",
                    "id": "10",
                    "attributes": {
                        "shippingType": "standard",
                        "country": {"code": "US"},
                        "variantId": 10,
                        "shippingCost": {
                            "firstItem": {"amount": 475, "currency": "USD"},
                            "additionalItems": {"amount": 240, "currency": "USD"},
                        },
                    },
                },
                {
                    "type": "variant_shipping_standard_us",
                    "id": "11",
                    "attributes": {
                        "shippingType": "standard",
                        "country": {"code": "US"},
                        "variantId": 11,
                        "shippingCost": {
                            "firstItem": {"amount": 495, "currency": "USD"},
                            "additionalItems": {"amount": 240, "currency": "USD"},
                        },
                    },
                },
                {
                    "type": "variant_shipping_standard_ca",
                    "id": "10",
                    "attributes": {
                        "shippingType": "standard",
                        "country": {"code": "CA"},
                        "variantId": 10,
                        "shippingCost": {
                            "firstItem": {"amount": 1200, "currency": "USD"},
                            "additionalItems": {"amount": 600, "currency": "USD"},
                        },
                    },
                },
            ]
        }


def test_build_shipping_snapshot_is_sanitized_complete_and_conservative():
    snapshot = build_shipping_snapshot(
        FakePrintify(),
        product_id="6a9860cc0bf15ba9490bfe3a",
        observed_at="2026-09-06T20:00:00-07:00",
    )

    assert snapshot["mode"] == "read_only"
    assert snapshot["external_account_writes"] == 0
    assert snapshot["source_product"] == {
        "id": "6a9860cc0bf15ba9490bfe3a",
        "blueprint_id": 6,
        "print_provider_id": 99,
        "enabled_variant_count": 2,
    }
    assert snapshot["us_standard"]["maximum_first_item_cost_cents"] == 495
    assert snapshot["us_standard"]["first_item_cost_cents"] == [475, 495]
    assert snapshot["us_standard"]["covered_enabled_variant_ids"] == [10, 11]
    assert snapshot["us_standard"]["groups"] == [
        {
            "enabled_variant_ids": [10],
            "first_item_cost_cents": 475,
            "additional_item_cost_cents": 240,
            "currency": "USD",
        },
        {
            "enabled_variant_ids": [11],
            "first_item_cost_cents": 495,
            "additional_item_cost_cents": 240,
            "currency": "USD",
        },
    ]


@pytest.mark.parametrize(
    "shipping_payload, message",
    [
        ({"data": "bad"}, "data"),
        ({"data": []}, "cover every enabled variant"),
        (
            {
                "data": [
                    {
                        "attributes": {
                            "shippingType": "standard",
                            "country": {"code": "US"},
                            "variantId": 10,
                            "shippingCost": {
                                "firstItem": {"amount": 475, "currency": "EUR"},
                                "additionalItems": {"amount": 240, "currency": "EUR"},
                            },
                        }
                    }
                ]
            },
            "USD",
        ),
    ],
)
def test_build_shipping_snapshot_fails_closed_on_incomplete_rates(
    shipping_payload, message
):
    class Malformed(FakePrintify):
        def get_catalog_standard_shipping(self, blueprint_id, print_provider_id):
            return shipping_payload

    with pytest.raises(DraftError, match=message):
        build_shipping_snapshot(
            Malformed(),
            product_id="6a9860cc0bf15ba9490bfe3a",
            observed_at="2026-09-06T20:00:00-07:00",
        )


def test_build_shipping_snapshot_rejects_conflicting_duplicate_variant_rates():
    class Duplicate(FakePrintify):
        def get_catalog_standard_shipping(self, blueprint_id, print_provider_id):
            payload = super().get_catalog_standard_shipping(
                blueprint_id, print_provider_id
            )
            conflicting = copy.deepcopy(payload["data"][0])
            conflicting["attributes"]["shippingCost"]["firstItem"]["amount"] = 499
            payload["data"].append(conflicting)
            return payload

    with pytest.raises(DraftError, match="conflicting"):
        build_shipping_snapshot(
            Duplicate(),
            product_id="6a9860cc0bf15ba9490bfe3a",
            observed_at="2026-09-06T20:00:00-07:00",
        )


def test_build_shipping_snapshot_collapses_equivalent_duplicate_rows():
    class Duplicate(FakePrintify):
        def get_catalog_standard_shipping(self, blueprint_id, print_provider_id):
            payload = super().get_catalog_standard_shipping(
                blueprint_id, print_provider_id
            )
            payload["data"].append(copy.deepcopy(payload["data"][0]))
            return payload

    snapshot = build_shipping_snapshot(
        Duplicate(),
        product_id="6a9860cc0bf15ba9490bfe3a",
        observed_at="2026-09-06T20:00:00-07:00",
    )
    assert snapshot["us_standard"]["equivalent_duplicate_rows_collapsed"] == 1
