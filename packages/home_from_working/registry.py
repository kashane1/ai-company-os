"""Pure, conservative normalization for HomeFromWorking catalog evidence.

The registry is deliberately derived from snapshots.  It contains references and
states, never raw API responses, and it never suggests an external mutation.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

SCHEMA_VERSION = 1
BANANA_KEYS = {
    "banana-berries-20260902/banana-berries-1",
    "banana-berries-20260902/banana-berries-2",
}


def _items(
    snapshot: object, names: tuple[str, ...], *, source: str
) -> list[Mapping[str, Any]]:
    """Return a snapshot collection, rejecting malformed entries rather than dropping them."""
    if snapshot is None:
        return []
    if isinstance(snapshot, list):
        entries = snapshot
    elif isinstance(snapshot, Mapping):
        for name in names:
            value = snapshot.get(name)
            if isinstance(value, list):
                entries = value
                break
        else:
            raise ValueError(
                "snapshot must be a list or an object containing a supported item list"
            )
    else:
        raise ValueError("snapshot must be a list or an object containing a supported item list")

    normalized: list[Mapping[str, Any]] = []
    for index, item in enumerate(entries, start=1):
        if not isinstance(item, Mapping):
            raise ValueError(f"{source} snapshot entry {index} must be an object")
        normalized.append(item)
    return normalized


def _identifier(value: object) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate or None


def _external_id(product: Mapping[str, Any]) -> str | None:
    external = product.get("external")
    if isinstance(external, Mapping):
        return _identifier(external.get("id"))
    return _identifier(product.get("external_id") or product.get("listing_id"))


def _product_id(product: Mapping[str, Any]) -> str | None:
    return _identifier(product.get("id") or product.get("product_id"))


def _listing_id(listing: Mapping[str, Any]) -> str | None:
    return _identifier(listing.get("listing_id") or listing.get("id"))


def _artwork_hash(item: Mapping[str, Any]) -> str | None:
    artwork = item.get("artwork")
    if isinstance(artwork, Mapping):
        return _identifier(artwork.get("sha256"))
    return _identifier(item.get("artwork_sha256"))


def _design_key(item: Mapping[str, Any]) -> str | None:
    return _identifier(item.get("design_key") or item.get("design"))


def _copy_title(item: Mapping[str, Any]) -> str | None:
    copy = item.get("copy")
    if isinstance(copy, Mapping):
        return _identifier(copy.get("title"))
    return _identifier(item.get("title"))


def _canonical_local(record: Mapping[str, Any], *, printify_snapshot_supplied: bool, etsy_snapshot_supplied: bool) -> dict[str, Any]:
    key = str(record["key"])
    return {
        "record_id": key,
        "provenance": {"local": ["catalog"], "printify": [], "etsy": []},
        "match": {"method": "local_catalog", "confidence": "historical"},
        "local": {
            "state": "historical",
            "key": key,
            "status": record.get("status", "unknown"),
            "product_id": _identifier(record.get("product_id")),
            "design_key": _design_key(record),
            "artwork_sha256": _artwork_hash(record),
            "title": _copy_title(record),
        },
        "live": {
            "printify": {"state": "missing" if printify_snapshot_supplied else "unknown"},
            "etsy": {"state": "missing" if etsy_snapshot_supplied else "unknown"},
        },
        "relationships": {"multi_product_listings": []},
        "discrepancies": [],
        "next_action": "supply_live_snapshots",
    }


def _append_discrepancy(record: dict[str, Any], discrepancy: str) -> None:
    if discrepancy not in record["discrepancies"]:
        record["discrepancies"].append(discrepancy)


def _unique_local_index(
    records: list[dict[str, Any]], key_name: str
) -> tuple[dict[Any, dict[str, Any]], dict[Any, list[dict[str, Any]]]]:
    """Index local identifiers only where exactly one catalog record owns them."""
    buckets: dict[Any, list[dict[str, Any]]] = {}
    for record in records:
        key = record["local"].get(key_name)
        if key:
            buckets.setdefault(key, []).append(record)
    return (
        {key: values[0] for key, values in buckets.items() if len(values) == 1},
        {key: values for key, values in buckets.items() if len(values) > 1},
    )


def _unique_design_art_index(
    records: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        design = record["local"].get("design_key")
        artwork = record["local"].get("artwork_sha256")
        if design and artwork:
            buckets.setdefault((design, artwork), []).append(record)
    return (
        {key: values[0] for key, values in buckets.items() if len(values) == 1},
        {key: values for key, values in buckets.items() if len(values) > 1},
    )


def _set_next_action(record: dict[str, Any]) -> None:
    printify = record["live"]["printify"]["state"]
    etsy = record["live"]["etsy"]["state"]
    if any(item.startswith("duplicate_local_") for item in record["discrepancies"]):
        record["next_action"] = "resolve_local_identifier_collision"
    elif record["record_id"] in BANANA_KEYS and printify == "confirmed_missing":
        record["next_action"] = "do_not_recreate_automatically"
    elif record["local"]["state"] == "absent" and etsy == "present":
        record["next_action"] = "review_unmatched_etsy_listing"
    elif record["local"]["state"] == "absent" and printify == "present":
        record["next_action"] = "review_unmatched_printify_product"
    elif printify == "unknown" or etsy == "unknown":
        record["next_action"] = "supply_live_snapshots"
    elif printify in {"missing", "confirmed_missing"}:
        record["next_action"] = "review_missing_printify_product"
    else:
        record["next_action"] = "review_discrepancies"


def _new_printify_record(product: Mapping[str, Any]) -> dict[str, Any]:
    product_id = _product_id(product)
    assert product_id is not None
    return {
        "record_id": f"printify:{product_id}",
        "provenance": {"local": [], "printify": ["snapshot"], "etsy": []},
        "match": {"method": "unmatched", "confidence": "none"},
        "local": {"state": "absent"},
        "live": {
            "printify": {"state": "present", "id": product_id},
            "etsy": {"state": "unknown"},
        },
        "relationships": {"multi_product_listings": []},
        "discrepancies": ["printify_only_record"],
        "next_action": "review_unmatched_printify_product",
    }


def _validated_receipts(
    receipts: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Validate receipt relationships before they can affect registry linkage."""
    normalized: list[Mapping[str, Any]] = []
    for index, receipt in enumerate(receipts, start=1):
        if not isinstance(receipt, Mapping):
            raise ValueError(f"multi-product receipt {index} must be an object")
        if not _identifier(receipt.get("multi_product_listing_id")):
            raise ValueError(f"multi-product receipt {index} has no listing id")
        members = receipt.get("members")
        if not isinstance(members, Mapping) or not members:
            raise ValueError(f"multi-product receipt {index} has no members object")
        if any(not _identifier(member) for member in members.values()):
            raise ValueError(f"multi-product receipt {index} has an invalid member id")
        normalized.append(receipt)
    return normalized


def build_registry(
    catalog: Mapping[str, Any],
    *,
    printify_snapshot: object | None = None,
    etsy_snapshot: object | None = None,
    multi_product_receipts: Iterable[Mapping[str, Any]] = (),
    generated_at: str,
) -> dict[str, Any]:
    """Build a registry using only supplied local artifacts and snapshots.

    Identity precedence is explicit: identifiers, then exact design+artwork;
    equal titles are merely a review hint and never establish a relationship.
    """
    printify_supplied = printify_snapshot is not None
    etsy_supplied = etsy_snapshot is not None
    products = _items(
        printify_snapshot, ("data", "products", "results"), source="Printify"
    )
    listings = _items(etsy_snapshot, ("results", "listings", "data"), source="Etsy")
    receipts = _validated_receipts(multi_product_receipts)
    catalog_records = catalog.get("records")
    if not isinstance(catalog_records, list):
        raise ValueError("catalog records must be a list")
    locals_: list[dict[str, Any]] = []
    for index, item in enumerate(catalog_records, start=1):
        if not isinstance(item, Mapping):
            raise ValueError(f"catalog record {index} must be an object")
        key = item.get("key")
        if not isinstance(key, str) or not key.strip() or key != key.strip():
            raise ValueError(f"catalog record {index} has an invalid key")
        locals_.append(
            _canonical_local(
                item,
                printify_snapshot_supplied=printify_supplied,
                etsy_snapshot_supplied=etsy_supplied,
            )
        )
    records: dict[str, dict[str, Any]] = {}
    for record in locals_:
        record_id = record["record_id"]
        if record_id in records:
            raise ValueError(f"duplicate local catalog key: {record_id}")
        records[record_id] = record
    by_product, duplicate_products = _unique_local_index(locals_, "product_id")
    by_design_art, duplicate_design_art = _unique_design_art_index(locals_)
    for product_id, candidates in duplicate_products.items():
        for candidate in candidates:
            _append_discrepancy(candidate, f"duplicate_local_product_id:{product_id}")
            candidate["match"] = {"method": "ambiguous_local_identifier", "confidence": "none"}
    for (design, artwork), candidates in duplicate_design_art.items():
        for candidate in candidates:
            _append_discrepancy(candidate, f"duplicate_local_design_and_artwork:{design}:{artwork}")
            candidate["match"] = {"method": "ambiguous_local_identifier", "confidence": "none"}
    by_printify: dict[str, dict[str, Any]] = {}
    external_listing: dict[str, dict[str, Any]] = {}

    for product in sorted(products, key=lambda item: _product_id(item) or ""):
        product_id = _product_id(product)
        if product_id is None:
            raise ValueError("Printify snapshot entry has no product id")
        if product_id in by_printify:
            raise ValueError(f"duplicate Printify product id: {product_id}")
        ambiguity: str | None = None
        target = by_product.get(product_id)
        method = "printify_product_id"
        confidence = "high"
        if product_id in duplicate_products:
            ambiguity = "ambiguous_local_product_id"
        elif target is None:
            design_art = (_design_key(product), _artwork_hash(product))
            if design_art in duplicate_design_art:
                ambiguity = "ambiguous_local_design_and_artwork"
            else:
                target = by_design_art.get(design_art)
            method, confidence = "design_key_and_artwork_sha256", "medium" if target else "none"
        if target is None:
            target = _new_printify_record(product)
            if ambiguity:
                target["match"] = {"method": ambiguity, "confidence": "none"}
                _append_discrepancy(target, ambiguity)
                if ambiguity == "ambiguous_local_product_id":
                    _append_discrepancy(target, f"duplicate_local_product_id:{product_id}")
                else:
                    design, artwork = _design_key(product), _artwork_hash(product)
                    _append_discrepancy(
                        target, f"duplicate_local_design_and_artwork:{design}:{artwork}"
                    )
            synthetic_record_id = target["record_id"]
            if synthetic_record_id in records:
                raise ValueError(
                    "synthetic registry id collides with local catalog key: "
                    f"{synthetic_record_id}"
                )
            records[synthetic_record_id] = target
        else:
            target["match"] = {"method": method, "confidence": confidence}
            target["provenance"]["printify"].append("snapshot")
            target["live"]["printify"] = {"state": "present", "id": product_id}
        by_printify[product_id] = target
        linked_listing_id = _external_id(product)
        if linked_listing_id:
            if linked_listing_id in external_listing:
                raise ValueError(
                    f"duplicate Printify external listing id: {linked_listing_id}"
                )
            external_listing[linked_listing_id] = target

    seen_listing_ids: set[str] = set()
    for listing in sorted(listings, key=lambda item: _listing_id(item) or ""):
        listing_id = _listing_id(listing)
        if listing_id is None:
            raise ValueError("Etsy snapshot entry has no listing id")
        if listing_id in seen_listing_ids:
            raise ValueError(f"duplicate Etsy listing id: {listing_id}")
        seen_listing_ids.add(listing_id)
        linked_product = _identifier(listing.get("printify_product_id") or listing.get("product_id"))
        target = by_printify.get(linked_product or "") or external_listing.get(listing_id)
        if target is None:
            synthetic_record_id = f"etsy:{listing_id}"
            if synthetic_record_id in records:
                raise ValueError(
                    "synthetic registry id collides with local catalog key: "
                    f"{synthetic_record_id}"
                )
            target = {
                "record_id": synthetic_record_id,
                "provenance": {"local": [], "printify": [], "etsy": ["snapshot"]},
                "match": {"method": "unmatched", "confidence": "none"},
                "local": {"state": "absent"},
                "live": {"etsy": {"state": "present", "id": listing_id}, "printify": {"state": "unknown"}},
                "relationships": {"multi_product_listings": []},
                "discrepancies": ["etsy_only_record"],
                "next_action": "review_unmatched_etsy_listing",
            }
            records[synthetic_record_id] = target
        else:
            target["provenance"]["etsy"].append("snapshot")
            target["live"]["etsy"] = {"state": "present", "id": listing_id}
            if "printify_only_record" in target["discrepancies"]:
                target["discrepancies"].remove("printify_only_record")
            if target["match"]["method"] == "unmatched":
                target["match"] = {"method": "etsy_listing_id_or_printify_external_id", "confidence": "high"}

    for receipt in receipts:
        group_id = _identifier(receipt.get("multi_product_listing_id"))
        members = receipt.get("members")
        assert group_id is not None
        assert isinstance(members, Mapping)
        for product_id in sorted({_identifier(value) for value in members.values()} - {None}):
            target = by_product.get(product_id) or by_printify.get(product_id)
            if target is not None and group_id not in target["relationships"]["multi_product_listings"]:
                target["relationships"]["multi_product_listings"].append(group_id)

    for record in records.values():
        groups = sorted(record["relationships"]["multi_product_listings"])
        record["relationships"]["multi_product_listings"] = groups
        if len(groups) > 1:
            _append_discrepancy(record, f"parallel_multi_product_receipts:{','.join(groups)}")
        if record["record_id"] in BANANA_KEYS:
            _append_discrepancy(record, "historical_unresolved")
            if printify_supplied and record["live"]["printify"]["state"] == "missing":
                record["live"]["printify"]["state"] = "confirmed_missing"
        title = record.get("local", {}).get("title")
        if title:
            for product in products:
                if _copy_title(product) == title and record["live"]["printify"]["state"] != "present":
                    _append_discrepancy(record, "title_only_candidate_present")
            for candidate in records.values():
                if candidate is record or candidate["local"]["state"] != "absent":
                    continue
                product_id = candidate["live"]["printify"].get("id")
                product = next((item for item in products if _product_id(item) == product_id), None)
                if product and _copy_title(product) == title:
                    _append_discrepancy(candidate, f"title_only_candidate:{record['record_id']}")
        _set_next_action(record)
        record["discrepancies"].sort()

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "evidence": {
            "catalog": "supplied",
            "printify_snapshot_supplied": printify_supplied,
            "etsy_snapshot_supplied": etsy_supplied,
            "multi_product_receipt_count": len(receipts),
        },
        "records": [records[key] for key in sorted(records)],
    }


def serialize_registry(registry: Mapping[str, Any]) -> str:
    """Return stable JSON suitable for a committed derived state artifact."""
    return json.dumps(registry, indent=2, sort_keys=True) + "\n"
