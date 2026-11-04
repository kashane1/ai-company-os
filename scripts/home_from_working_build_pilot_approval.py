#!/usr/bin/env python3
"""Build a local, read-only approval packet for the existing Etsy pilot cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAIR_EVIDENCE = (
    REPO_ROOT
    / "state/home-from-working/operations/evidence/2026-09-07/pilot-existing-active-pairs.json"
)
DEFAULT_ETSY_SNAPSHOT = (
    REPO_ROOT / "state/home-from-working/operations/evidence/2026-09-07/etsy-shop.json"
)
DEFAULT_ETSY_UI_READBACK = (
    REPO_ROOT / "state/home-from-working/operations/evidence/2026-09-07/pilot-cohort-etsy-ui-readback.json"
)
DEFAULT_JSON_OUTPUT = (
    REPO_ROOT / "state/home-from-working/operations/pilot-cohort-approval-packet.json"
)
DEFAULT_MARKDOWN_OUTPUT = (
    REPO_ROOT / "state/home-from-working/operations/pilot-cohort-approval-packet.md"
)
PUBLIC_DETAIL_FIELDS = (
    "listing_id",
    "title",
    "description",
    "tags",
    "state",
    "shipping_profile_id",
    "return_policy_id",
    "created_timestamp",
    "updated_timestamp",
    "quantity",
    "who_made",
    "when_made",
)
UNPROVEN_UI_FIELDS = ("image_ids",)


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _listing_id(value: object, *, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive integer")
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive integer") from exc
    if parsed <= 0 or str(parsed) != str(value).strip():
        raise ValueError(f"{label} must be a positive integer")
    return parsed


def _inventory_evidence(listing: Mapping[str, Any]) -> dict[str, object]:
    inventory = listing.get("inventory")
    if not isinstance(inventory, list) or any(not isinstance(row, Mapping) for row in inventory):
        raise ValueError(f"listing {listing.get('listing_id')} inventory must be a list of objects")
    properties: set[str] = set()
    garment_values: set[str] = set()
    enabled_offerings = 0
    disabled_offerings = 0
    prices: Counter[tuple[str | None, int | None]] = Counter()
    price_points: Counter[tuple[int, str | None, int | None]] = Counter()
    for row in inventory:
        property_values = row.get("property_values")
        if not isinstance(property_values, list):
            raise ValueError(f"listing {listing.get('listing_id')} property_values must be a list")
        for property_value in property_values:
            if not isinstance(property_value, Mapping):
                raise ValueError(f"listing {listing.get('listing_id')} property value must be an object")
            property_name = property_value.get("property_name")
            if isinstance(property_name, str):
                properties.add(property_name)
            values = property_value.get("values")
            if isinstance(values, list) and property_name in {"Size", "Clothing sizes"}:
                garment_values.update(value for value in values if isinstance(value, str))
        offerings = row.get("offerings")
        if not isinstance(offerings, list):
            raise ValueError(f"listing {listing.get('listing_id')} offerings must be a list")
        for offering in offerings:
            if not isinstance(offering, Mapping):
                raise ValueError(f"listing {listing.get('listing_id')} offering must be an object")
            if offering.get("is_enabled") is True:
                enabled_offerings += 1
            else:
                disabled_offerings += 1
            price = offering.get("price")
            if isinstance(price, Mapping):
                amount = price.get("amount")
                divisor = price.get("divisor")
                currency = price.get("currency_code")
                if isinstance(amount, int) and not isinstance(amount, bool):
                    normalized_currency = currency if isinstance(currency, str) else None
                    normalized_divisor = (
                        divisor
                        if isinstance(divisor, int)
                        and not isinstance(divisor, bool)
                        and divisor > 0
                        else None
                    )
                    prices[(normalized_currency, normalized_divisor)] += 1
                    price_points[(amount, normalized_currency, normalized_divisor)] += 1
    return {
        "source_inventory_sha256": _canonical_hash(inventory),
        "inventory_row_count": len(inventory),
        "enabled_offering_count": enabled_offerings,
        "disabled_or_unproven_offering_count": disabled_offerings,
        "property_names": sorted(properties),
        "garment_values_observed": sorted(garment_values),
        "price_currency_divisor_counts": [
            {"currency_code": currency, "divisor": divisor, "offering_count": count}
            for (currency, divisor), count in sorted(
                prices.items(), key=lambda item: (item[0][0] or "", item[0][1] or 0)
            )
        ],
        "price_points": [
            {
                "amount": amount,
                "currency_code": currency,
                "divisor": divisor,
                "offering_count": count,
            }
            for (amount, currency, divisor), count in sorted(
                price_points.items(), key=lambda item: (item[0][1] or "", item[0][2] or 0, item[0][0])
            )
        ],
    }


def _ui_readback_by_listing(ui_readback: Mapping[str, Any]) -> tuple[dict[str, object], dict[int, dict[str, object]]]:
    if ui_readback.get("mode") != "read_only" or ui_readback.get("external_account_writes") != 0:
        raise ValueError("Etsy UI readback must be read-only with zero external account writes")
    common = _mapping(ui_readback.get("common_settings"), label="Etsy UI readback common_settings")
    production_partner = common.get("production_partner")
    buyer_label = common.get("production_partner_buyer_label")
    processing_profile = _mapping(common.get("processing_profile"), label="Etsy UI readback processing_profile")
    if not isinstance(production_partner, str) or not production_partner:
        raise ValueError("Etsy UI readback must prove a production partner")
    if not isinstance(buyer_label, str) or not buyer_label:
        raise ValueError("Etsy UI readback must prove a production-partner buyer label")
    if not all(isinstance(processing_profile.get(field), str) and processing_profile[field] for field in ("type", "time")):
        raise ValueError("Etsy UI readback must prove a processing profile type and time")

    listings = ui_readback.get("per_listing")
    if not isinstance(listings, list):
        raise ValueError("Etsy UI readback per_listing must be a list")
    summary_listing_ids = ui_readback.get("listing_ids")
    if not isinstance(summary_listing_ids, list):
        raise ValueError("Etsy UI readback listing_ids must be a list")
    parsed_summary_listing_ids = {
        _listing_id(value, label="Etsy UI readback summary listing_id") for value in summary_listing_ids
    }
    if len(parsed_summary_listing_ids) != len(summary_listing_ids):
        raise ValueError("Etsy UI readback summary listing IDs must be unique")
    readback_by_id: dict[int, dict[str, object]] = {}
    for value in listings:
        listing = _mapping(value, label="Etsy UI readback listing")
        listing_id = _listing_id(listing.get("listing_id"), label="Etsy UI readback listing_id")
        if listing_id in readback_by_id:
            raise ValueError(f"duplicate Etsy UI readback listing ID: {listing_id}")
        image_count = listing.get("image_count")
        if not isinstance(image_count, int) or isinstance(image_count, bool) or image_count < 0:
            raise ValueError(f"Etsy UI readback listing {listing_id} must have a non-negative image count")
        if listing.get("settings_match_common") is not True:
            raise ValueError(f"Etsy UI readback listing {listing_id} does not match common settings")
        readback_by_id[listing_id] = {"image_count": image_count}
    if parsed_summary_listing_ids != set(readback_by_id):
        raise ValueError("Etsy UI readback summary listing IDs must match per-listing evidence")
    return (
        {
            "production_partner": production_partner,
            "production_partner_buyer_label": buyer_label,
            "processing_profile": {
                "type": processing_profile["type"],
                "time": processing_profile["time"],
            },
        },
        readback_by_id,
    )


def _listing_packet(
    listing: Mapping[str, Any],
    *,
    pair_id: str,
    role: str,
    format_name: str,
    format_evidence: object,
    ui_common_settings: Mapping[str, object],
    ui_listing_evidence: Mapping[str, object],
) -> dict[str, object]:
    exact_details = {field: listing[field] for field in PUBLIC_DETAIL_FIELDS if field in listing}
    if set(("listing_id", "title", "description", "state")) - set(exact_details):
        raise ValueError(f"listing {listing.get('listing_id')} lacks required current public details")
    omitted = [field for field in UNPROVEN_UI_FIELDS if field not in listing]
    return {
        "listing_id": str(listing["listing_id"]),
        "intended_pair_role": role,
        "pair_id": pair_id,
        "format": format_name,
        "format_evidence": format_evidence,
        "exact_current_public_details": exact_details,
        "inventory_evidence": _inventory_evidence(listing),
        "ui_readback_evidence": {
            "image_count": ui_listing_evidence["image_count"],
            "production_partner": ui_common_settings["production_partner"],
            "production_partner_buyer_label": ui_common_settings["production_partner_buyer_label"],
            "processing_profile": ui_common_settings["processing_profile"],
        },
        "protected_fields": {
            "policy": "freeze_no_change",
            "fields": [
                "title",
                "tags",
                "description",
                "images",
                "price",
                "inventory_and_variations",
                "shipping_profile",
                "return_policy",
                "publication_state",
            ],
            "source_listing_sha256": _canonical_hash(listing),
            "source_inventory_sha256": _canonical_hash(listing["inventory"]),
        },
        "unproven_or_omitted_ui_fields": omitted,
        "proposed_action": {
            "kind": "freeze_existing_listing_for_observation",
            "external_account_writes": 0,
        },
    }


def build_packet(
    pair_evidence: Mapping[str, Any],
    etsy_snapshot: Mapping[str, Any],
    etsy_ui_readback: Mapping[str, Any],
    *,
    sources: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Build the exact existing-listing cohort packet without inferring UI state."""

    ui_common_settings, ui_by_listing = _ui_readback_by_listing(etsy_ui_readback)
    pairs = pair_evidence.get("supported_pairs")
    if not isinstance(pairs, list) or len(pairs) != 4:
        raise ValueError("pilot evidence must contain exactly four supported pairs")
    expected_ui_listing_ids: set[int] = set()
    for pair_value in pairs:
        pair = _mapping(pair_value, label="pilot pair")
        for role in ("control", "treatment"):
            arm = _mapping(pair.get(role), label=f"pilot pair {pair.get('pair_id')} {role}")
            expected_ui_listing_ids.add(
                _listing_id(arm.get("etsy_listing_id"), label=f"pilot pair {pair.get('pair_id')} {role} listing ID")
            )
    if len(expected_ui_listing_ids) != 8 or set(ui_by_listing) != expected_ui_listing_ids:
        raise ValueError("Etsy UI readback must cover exactly the eight cohort listing IDs")
    summary = _mapping(pair_evidence.get("snapshot_summary"), label="pilot evidence snapshot_summary")
    if summary.get("supported_active_listing_count") != 8:
        raise ValueError("pilot evidence must name exactly eight supported active listings")
    snapshot_listings = etsy_snapshot.get("listings")
    if not isinstance(snapshot_listings, list):
        raise ValueError("Etsy snapshot listings must be a list")
    listings_by_id: dict[int, Mapping[str, Any]] = {}
    for source_listing in snapshot_listings:
        listing = _mapping(source_listing, label="Etsy snapshot listing")
        listing_id = _listing_id(listing.get("listing_id"), label="Etsy snapshot listing_id")
        if listing_id in listings_by_id:
            raise ValueError(f"duplicate Etsy snapshot listing ID: {listing_id}")
        listings_by_id[listing_id] = listing

    packet_pairs: list[dict[str, object]] = []
    seen_listing_ids: set[int] = set()
    for pair_value in pairs:
        pair = _mapping(pair_value, label="pilot pair")
        pair_id = pair.get("pair_id")
        if not isinstance(pair_id, str) or not pair_id:
            raise ValueError("pilot pair must have an ID")
        arms: list[dict[str, object]] = []
        for role in ("control", "treatment"):
            arm = _mapping(pair.get(role), label=f"pilot pair {pair_id} {role}")
            listing_id = _listing_id(arm.get("etsy_listing_id"), label=f"pilot pair {pair_id} {role} listing ID")
            if listing_id in seen_listing_ids:
                raise ValueError(f"duplicate cohort listing ID: {listing_id}")
            seen_listing_ids.add(listing_id)
            listing = listings_by_id.get(listing_id)
            if listing is None:
                raise ValueError(f"pilot listing {listing_id} is missing from Etsy snapshot")
            if listing.get("title") != arm.get("title"):
                raise ValueError(f"pilot listing {listing_id} title does not match pilot evidence")
            if listing.get("state") != "active":
                raise ValueError(f"pilot listing {listing_id} is not active in Etsy snapshot")
            arms.append(
                _listing_packet(
                    listing,
                    pair_id=pair_id,
                    role=role,
                    format_name=str(arm.get("format")),
                    format_evidence=arm.get("format_evidence"),
                    ui_common_settings=ui_common_settings,
                    ui_listing_evidence=ui_by_listing[listing_id],
                )
            )
        packet_pairs.append(
            {
                "pair_id": pair_id,
                "buyer_intent": pair.get("buyer_intent"),
                "match_evidence": pair.get("match_evidence"),
                "listings": arms,
            }
        )
    if len(seen_listing_ids) != 8:
        raise ValueError("pilot cohort must contain exactly eight unique existing listings")

    packet: dict[str, object] = {
        "schema_version": 1,
        "status": "approval_packet_pending_founder",
        "read_only": True,
        "external_account_writes": 0,
        "sources": sources
        or [
            {
                "kind": "pilot_evidence",
                "observed_at": str(pair_evidence.get("observed_at", "unknown")),
                "sha256": _canonical_hash(pair_evidence),
            },
            {
                "kind": "etsy_snapshot",
                "observed_at": str(etsy_snapshot.get("observed_at", "unknown")),
                "sha256": _canonical_hash(etsy_snapshot),
            },
            {
                "kind": "etsy_ui_readback",
                "observed_at": str(etsy_ui_readback.get("observed_at", "unknown")),
                "sha256": _canonical_hash(etsy_ui_readback),
            },
        ],
        "cohort": {
            "name": "existing_active_four_pair_product_format_observation",
            "pair_count": 4,
            "listing_count": 8,
            "selection_rule": "only live Etsy IDs supported by current active-pair evidence",
            "no_new_listing_inferred": True,
        },
        "default_recommendation": {
            "action": "freeze_existing_listings_no_public_change",
            "rationale": "Observe the already-active shirt-only versus three-garment format pairs without changing unrelated title, tags, descriptions, images, prices, inventory, shipping, returns, production-partner settings, or publication state.",
        },
        "publication": {
            "approved": False,
            "requires_separate_founder_approval": True,
            "included_in_this_packet": False,
        },
        "approval": {
            "required": True,
            "scope": "exact_packet_revision_existing_listing_observation_only",
            "approved": False,
        },
        "pairs": packet_pairs,
    }
    packet["revision_sha256"] = _canonical_hash(packet)
    return packet


def render_markdown(packet: Mapping[str, Any]) -> str:
    lines = [
        "# HomeFromWorking existing-listing pilot approval packet",
        "",
        f"Revision SHA-256: `{packet['revision_sha256']}`",
        "",
        "Status: approval packet only. No Etsy or Printify change was made.",
        "",
        "## Decision requested",
        "",
        "Approve or decline observation of this exact four-pair, eight-listing cohort. This does not approve publication or any listing edit.",
        "",
        "## Default recommendation",
        "",
        str(_mapping(packet["default_recommendation"], label="packet recommendation")["rationale"]),
        "",
    ]
    for pair in packet["pairs"]:
        pair_data = _mapping(pair, label="packet pair")
        lines.extend([f"## {pair_data['pair_id']}", "", f"Buyer intent: {pair_data['buyer_intent']}", "", f"Match evidence: {pair_data['match_evidence']}", ""])
        for listing in pair_data["listings"]:
            listing_data = _mapping(listing, label="packet listing")
            details = _mapping(listing_data["exact_current_public_details"], label="public details")
            ui_evidence = _mapping(listing_data["ui_readback_evidence"], label="UI readback evidence")
            processing_profile = _mapping(ui_evidence["processing_profile"], label="UI processing profile")
            lines.extend(
                [
                    f"### {listing_data['intended_pair_role']} — Etsy {listing_data['listing_id']}",
                    "",
                    f"Format: `{listing_data['format']}`. {listing_data['format_evidence']}",
                    "",
                    f"Current title: {details['title']}",
                    "",
                    (
                        f"Current state: `{details['state']}`; shipping profile: "
                        f"`{details.get('shipping_profile_id', 'not captured')}`; return policy: "
                        f"`{details.get('return_policy_id', 'not captured')}`."
                    ),
                    "",
                    "Current description:",
                    "",
                    str(details["description"]),
                    "",
                    f"Current tags: {', '.join(str(tag) for tag in details.get('tags', []))}",
                    "",
                    (
                        f"UI readback: `{ui_evidence['image_count']}` images; production partner: "
                        f"`{ui_evidence['production_partner']}`; processing profile: "
                        f"`{processing_profile['type']}` / `{processing_profile['time']}`."
                    ),
                    "",
                    "Inventory evidence (exact snapshot-derived values):",
                    "",
                    "```json",
                    json.dumps(
                        {
                            "disabled_or_unproven_offering_count": listing_data["inventory_evidence"]["disabled_or_unproven_offering_count"],
                            "enabled_offering_count": listing_data["inventory_evidence"]["enabled_offering_count"],
                            "garment_values_observed": listing_data["inventory_evidence"]["garment_values_observed"],
                            "inventory_row_count": listing_data["inventory_evidence"]["inventory_row_count"],
                            "price_points": listing_data["inventory_evidence"]["price_points"],
                            "property_names": listing_data["inventory_evidence"]["property_names"],
                        },
                        indent=2,
                        sort_keys=True,
                    ),
                    "```",
                    "",
                    "Protected by default: title, tags, description, images, price, inventory/variations, shipping, returns, and publication state. No change proposed.",
                    "",
                    "Snapshot does not prove: " + ", ".join(listing_data["unproven_or_omitted_ui_fields"]),
                    "",
                ]
            )
    lines.extend(
        [
            "## Publication boundary",
            "",
            "`publication.approved` is `false`. Any listing edit, new listing, activation, deactivation, or publication needs separate founder approval bound to a later exact revision.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-evidence", type=Path, default=DEFAULT_PAIR_EVIDENCE)
    parser.add_argument("--etsy-snapshot", type=Path, default=DEFAULT_ETSY_SNAPSHOT)
    parser.add_argument("--etsy-ui-readback", type=Path, default=DEFAULT_ETSY_UI_READBACK)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    args = parser.parse_args(argv)
    try:
        evidence = _load_json(args.pair_evidence)
        snapshot = _load_json(args.etsy_snapshot)
        ui_readback = _load_json(args.etsy_ui_readback)
        packet = build_packet(
            evidence,
            snapshot,
            ui_readback,
            sources=[
                {"kind": "pilot_evidence", "path": str(args.pair_evidence), "sha256": _file_hash(args.pair_evidence)},
                {"kind": "etsy_snapshot", "path": str(args.etsy_snapshot), "sha256": _file_hash(args.etsy_snapshot)},
                {"kind": "etsy_ui_readback", "path": str(args.etsy_ui_readback), "sha256": _file_hash(args.etsy_ui_readback)},
            ],
        )
        _write(args.json_output, json.dumps(packet, indent=2, sort_keys=True) + "\n")
        _write(args.markdown_output, render_markdown(packet))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
                "revision_sha256": packet["revision_sha256"],
                "external_account_writes": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
