from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "scripts/home_from_working_build_pilot_approval.py"
SPEC = importlib.util.spec_from_file_location("home_from_working_build_pilot_approval", SCRIPT)
assert SPEC and SPEC.loader
approval = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(approval)


def _listing(listing_id: int, title: str) -> dict:
    return {
        "listing_id": listing_id,
        "title": title,
        "description": f"Exact current description for {listing_id}",
        "tags": ["one", "two"],
        "state": "active",
        "shipping_profile_id": 10,
        "return_policy_id": 20,
        "created_timestamp": 1,
        "updated_timestamp": 2,
        "quantity": 3,
        "who_made": "someone_else",
        "when_made": "made_to_order",
        "inventory": [
            {
                "property_values": [
                    {"property_name": "Size", "values": ["Heavy Blend Hoodie / M"]}
                ],
                "offerings": [{"is_enabled": True, "price": {"amount": 1999}}],
            }
        ],
    }


def _pair_evidence() -> dict:
    return {
        "observed_at": "2026-09-07",
        "snapshot_summary": {"supported_pair_count": 4, "supported_active_listing_count": 8},
        "supported_pairs": [
            {
                "pair_id": f"pair-{number}",
                "buyer_intent": "same buyer intent",
                "match_evidence": "same concept",
                "control": {
                    "etsy_listing_id": str(number * 10 + 1),
                    "format": "shirt_only",
                    "title": f"Control {number}",
                    "format_evidence": "shirt-only proof",
                },
                "treatment": {
                    "etsy_listing_id": str(number * 10 + 2),
                    "format": "shirt_hoodie_crewneck",
                    "title": f"Treatment {number}",
                    "format_evidence": "three-garment proof",
                },
            }
            for number in range(1, 5)
        ],
    }


def _snapshot() -> dict:
    listings = []
    for number in range(1, 5):
        listings.extend(
            [
                _listing(number * 10 + 1, f"Control {number}"),
                _listing(number * 10 + 2, f"Treatment {number}"),
            ]
        )
    return {"observed_at": "2026-09-07T06:28:08Z", "shop": {"shop_id": 1}, "listings": listings}


def _ui_readback() -> dict:
    return {
        "observed_at": "2026-09-07T16:45:44Z",
        "mode": "read_only",
        "external_account_writes": 0,
        "listing_ids": [str(number) for number in (11, 12, 21, 22, 31, 32, 41, 42)],
        "common_settings": {
            "production_partner": "Printify",
            "production_partner_buyer_label": "A print shop",
            "processing_profile": {"type": "Made to order", "time": "3-5 days"},
        },
        "per_listing": [
            {"listing_id": str(number), "image_count": 20, "settings_match_common": True}
            for number in (11, 12, 21, 22, 31, 32, 41, 42)
        ],
    }


def test_build_packet_binds_eight_existing_listing_ids_and_keeps_publication_unapproved() -> None:
    packet = approval.build_packet(_pair_evidence(), _snapshot(), _ui_readback())

    assert packet["publication"] == {
        "approved": False,
        "requires_separate_founder_approval": True,
        "included_in_this_packet": False,
    }
    assert len(packet["pairs"]) == 4
    assert [listing["listing_id"] for pair in packet["pairs"] for listing in pair["listings"]] == [
        "11", "12", "21", "22", "31", "32", "41", "42"
    ]
    assert packet["pairs"][0]["listings"][0]["proposed_action"] == {
        "kind": "freeze_existing_listing_for_observation",
        "external_account_writes": 0,
    }
    assert packet["pairs"][0]["listings"][1]["intended_pair_role"] == "treatment"
    assert packet["pairs"][0]["listings"][0]["exact_current_public_details"]["description"] == "Exact current description for 11"
    assert packet["pairs"][0]["listings"][0]["inventory_evidence"]["price_points"] == [
        {"amount": 1999, "currency_code": None, "divisor": None, "offering_count": 1}
    ]
    assert packet["pairs"][0]["listings"][0]["ui_readback_evidence"] == {
        "image_count": 20,
        "processing_profile": {"type": "Made to order", "time": "3-5 days"},
        "production_partner": "Printify",
        "production_partner_buyer_label": "A print shop",
    }
    assert packet["pairs"][0]["listings"][0]["unproven_or_omitted_ui_fields"] == ["image_ids"]
    assert len(packet["revision_sha256"]) == 64
    rendered = approval.render_markdown(packet)
    assert "Current state: `active`; shipping profile: `10`; return policy: `20`." in rendered
    assert "UI readback: `20` images; production partner: `Printify`; processing profile: `Made to order` / `3-5 days`." in rendered
    assert '"amount": 1999' in rendered


def test_build_packet_is_deterministic_and_fails_closed_for_missing_existing_listing() -> None:
    evidence = _pair_evidence()
    snapshot = _snapshot()
    ui_readback = _ui_readback()
    assert approval.build_packet(evidence, snapshot, ui_readback) == approval.build_packet(evidence, snapshot, ui_readback)

    snapshot["listings"] = snapshot["listings"][1:]
    with pytest.raises(ValueError, match="missing from Etsy snapshot"):
        approval.build_packet(evidence, snapshot, ui_readback)


def test_build_packet_fails_closed_when_readback_does_not_cover_every_listing() -> None:
    ui_readback = _ui_readback()
    ui_readback["per_listing"] = ui_readback["per_listing"][:-1]

    with pytest.raises(ValueError, match="listing IDs"):
        approval.build_packet(_pair_evidence(), _snapshot(), ui_readback)


def test_build_packet_fails_closed_when_readback_summary_disagrees_with_per_listing_evidence() -> None:
    ui_readback = _ui_readback()
    ui_readback["listing_ids"] = ui_readback["listing_ids"][:-1] + ["99"]

    with pytest.raises(ValueError, match="summary listing IDs must match per-listing evidence"):
        approval.build_packet(_pair_evidence(), _snapshot(), ui_readback)
