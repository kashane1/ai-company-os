#!/usr/bin/env python3
"""Apply one founder-approved Etsy trust-copy manifest, description fields only.

The command refuses to contact Etsy unless both the exact manifest digest and
an action-time description-only confirmation are supplied. It never creates,
publishes, prices, images, tags, inventory, shipping, or production-partner
records. A PATCH is followed by a GET readback and protected-field comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.config.secrets import get_secret
from packages.etsy.auth import (
    ACCESS_TOKEN_NAME,
    API_CREDENTIAL_NAME,
    EXPIRES_AT_NAME,
    EtsyCredentials,
)
from packages.etsy.client import EtsyDescriptionWriteClient


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "state/home-from-working/operations/trust-copy-change-preview.json"
PROTECTED_LISTING_FIELDS = (
    "listing_id",
    "shop_id",
    "title",
    "tags",
    "shipping_profile_id",
    "return_policy_id",
    "production_partner_ids",
    "who_made",
    "when_made",
    "state",
    "quantity",
    "price",
    "materials",
    "taxonomy_id",
    "type",
    "readiness_state_id",
    "should_auto_renew",
    "is_taxable",
    "is_personalizable",
    "personalization_is_required",
    "is_customizable",
    "is_vintage",
)


class ListingDescriptionClient(Protocol):
    def get_listing(self, listing_id: int) -> dict[str, Any]: ...

    def get_listing_inventory(self, listing_id: int) -> dict[str, Any]: ...

    def update_listing_description(
        self, shop_id: int, listing_id: int, description: str
    ) -> dict[str, Any]: ...


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _canonical_sha256(value: object) -> str:
    return _sha256_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    )


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _positive_int(value: object, *, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive integer")
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive integer") from exc
    if parsed <= 0 or str(parsed) != str(value).strip():
        raise ValueError(f"{label} must be a positive integer")
    return parsed


def _description_with_paragraph(description: str, paragraph: str) -> str:
    return description if paragraph in description else f"{description.rstrip()}\n\n{paragraph}"


def _protected_hash(listing: Mapping[str, Any], inventory: Mapping[str, Any]) -> str:
    return _canonical_sha256(
        {
            "listing": {field: listing.get(field) for field in PROTECTED_LISTING_FIELDS},
            "inventory": inventory,
        }
    )


def build_plan(
    manifest: Mapping[str, Any],
    source_snapshot: Mapping[str, Any],
    *,
    manifest_sha256: str = "test-manifest-sha256",
    source_snapshot_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate immutable manifest and snapshot inputs before any Etsy call."""

    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported manifest schema version")
    source = _mapping(manifest.get("source_snapshot"), label="manifest source_snapshot")
    expected_snapshot_hash = source.get("sha256")
    actual_snapshot_hash = source_snapshot_sha256 or _canonical_sha256(source_snapshot)
    if not isinstance(expected_snapshot_hash, str) or expected_snapshot_hash != actual_snapshot_hash:
        raise ValueError("source snapshot hash does not match the manifest")
    change = _mapping(manifest.get("change"), label="manifest change")
    paragraph = change.get("paragraph")
    if (
        change.get("field") != "description"
        or change.get("operation") != "append_exact_paragraph_once"
        or not isinstance(paragraph, str)
        or not paragraph.strip()
    ):
        raise ValueError("manifest must contain one exact description append operation")
    approval = _mapping(manifest.get("approval"), label="manifest approval")
    if approval.get("required") is not True or approval.get("scope") != "exact_manifest_revision_only":
        raise ValueError("manifest approval boundary is invalid")
    if approval.get("publication_approval_included") is not False:
        raise ValueError("manifest must not include publication approval")
    shop = _mapping(source_snapshot.get("shop"), label="source snapshot shop")
    shop_id = _positive_int(shop.get("shop_id"), label="source snapshot shop_id")
    listings = source_snapshot.get("listings")
    if not isinstance(listings, list):
        raise ValueError("source snapshot listings must be a list")
    by_listing_id: dict[int, Mapping[str, Any]] = {}
    for listing in listings:
        item = _mapping(listing, label="source snapshot listing")
        listing_id = _positive_int(item.get("listing_id"), label="source snapshot listing_id")
        if listing_id in by_listing_id:
            raise ValueError(f"duplicate source snapshot listing id: {listing_id}")
        by_listing_id[listing_id] = item
    targets = manifest.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("manifest targets must be a non-empty list")
    planned_targets: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for target in targets:
        item = _mapping(target, label="manifest target")
        listing_id = _positive_int(item.get("listing_id"), label="manifest target listing_id")
        if listing_id in seen_ids:
            raise ValueError(f"duplicate manifest target listing id: {listing_id}")
        seen_ids.add(listing_id)
        source_listing = by_listing_id.get(listing_id)
        if source_listing is None:
            raise ValueError(f"manifest target {listing_id} is absent from source snapshot")
        expected_title = item.get("title")
        source_title = source_listing.get("title")
        source_description = source_listing.get("description")
        if (
            not isinstance(expected_title, str)
            or expected_title != source_title
            or not isinstance(source_description, str)
        ):
            raise ValueError(f"manifest target {listing_id} does not match source snapshot")
        planned_targets.append(
            {
                "listing_id": listing_id,
                "record_key": item.get("record_key"),
                "title": expected_title,
                "source_description": source_description,
                "desired_description": _description_with_paragraph(source_description, paragraph),
            }
        )
    return {
        "manifest_sha256": manifest_sha256,
        "source_snapshot_sha256": actual_snapshot_hash,
        "shop_id": shop_id,
        "paragraph": paragraph,
        "targets": planned_targets,
    }


def load_plan(manifest_path: Path, *, approved_manifest_sha256: str) -> dict[str, Any]:
    manifest_bytes = manifest_path.read_bytes()
    actual_manifest_sha256 = _sha256_bytes(manifest_bytes)
    if approved_manifest_sha256 != actual_manifest_sha256:
        raise ValueError("approved manifest SHA-256 does not match the exact file")
    manifest = _mapping(json.loads(manifest_bytes), label="manifest")
    source = _mapping(manifest.get("source_snapshot"), label="manifest source_snapshot")
    declared_path = source.get("path")
    if not isinstance(declared_path, str) or not declared_path or Path(declared_path).is_absolute():
        raise ValueError("manifest source snapshot path must be a non-empty repo-relative path")
    snapshot_path = (REPO_ROOT / declared_path).resolve()
    if REPO_ROOT not in snapshot_path.parents:
        raise ValueError("manifest source snapshot path escapes the repository")
    snapshot_bytes = snapshot_path.read_bytes()
    snapshot = _mapping(json.loads(snapshot_bytes), label="source snapshot")
    return build_plan(
        manifest,
        snapshot,
        manifest_sha256=actual_manifest_sha256,
        source_snapshot_sha256=_sha256_bytes(snapshot_bytes),
    )


def _read_current(
    client: ListingDescriptionClient, target: Mapping[str, Any], shop_id: int
) -> dict[str, Any]:
    listing_id = int(target["listing_id"])
    listing = _mapping(client.get_listing(listing_id), label=f"live listing {listing_id}")
    if _positive_int(listing.get("listing_id"), label="live listing_id") != listing_id:
        raise ValueError(f"live listing {listing_id} returned a mismatched listing ID")
    if _positive_int(listing.get("shop_id"), label="live listing shop_id") != shop_id:
        raise ValueError(f"live listing {listing_id} is not owned by the source shop")
    if listing.get("title") != target["title"]:
        raise ValueError(f"live listing {listing_id} title drifted from the approved target")
    description = listing.get("description")
    if not isinstance(description, str):
        raise ValueError(f"live listing {listing_id} has no string description")
    inventory = _mapping(
        client.get_listing_inventory(listing_id), label=f"live listing {listing_id} inventory"
    )
    return {
        "listing": listing,
        "description": description,
        "protected_hash": _protected_hash(listing, inventory),
        "inventory_hash": _canonical_sha256(inventory),
    }


def _verify_readback(
    client: ListingDescriptionClient,
    target: Mapping[str, Any],
    shop_id: int,
    *,
    expected_protected_hash: str,
) -> dict[str, Any]:
    current = _read_current(client, target, shop_id)
    if current["description"] != target["desired_description"]:
        raise RuntimeError(f"post-action readback did not match listing {target['listing_id']} description")
    if current["protected_hash"] != expected_protected_hash:
        raise RuntimeError(f"post-action protected fields changed for listing {target['listing_id']}")
    return current


def apply_plan(client: ListingDescriptionClient, plan: Mapping[str, Any]) -> dict[str, Any]:
    """Apply a prevalidated plan with a complete GET preflight and GET readback."""

    shop_id = _positive_int(plan.get("shop_id"), label="plan shop_id")
    targets = plan.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("plan targets must be a non-empty list")
    prepared: list[dict[str, Any]] = []
    for target_value in targets:
        target = _mapping(target_value, label="plan target")
        current = _read_current(client, target, shop_id)
        if current["description"] == target["source_description"]:
            status = "apply"
        elif current["description"] == target["desired_description"]:
            status = "already_applied"
        else:
            raise ValueError(f"live listing {target['listing_id']} description drifted from the approved source")
        prepared.append({"target": target, "before": current, "status": status})

    receipt_targets: list[dict[str, Any]] = []
    for item in prepared:
        target = item["target"]
        before = item["before"]
        status = item["status"]
        if status == "apply":
            try:
                client.update_listing_description(
                    shop_id, int(target["listing_id"]), str(target["desired_description"])
                )
            except httpx.HTTPError:
                readback = _verify_readback(
                    client,
                    target,
                    shop_id,
                    expected_protected_hash=str(before["protected_hash"]),
                )
                status = "reconciled_after_write_error"
            else:
                readback = _verify_readback(
                    client,
                    target,
                    shop_id,
                    expected_protected_hash=str(before["protected_hash"]),
                )
                status = "applied"
        else:
            readback = _verify_readback(
                client,
                target,
                shop_id,
                expected_protected_hash=str(before["protected_hash"]),
            )
        receipt_targets.append(
            {
                "listing_id": target["listing_id"],
                "record_key": target.get("record_key"),
                "title": target["title"],
                "status": status,
                "pre_action_description_sha256": _sha256_text(str(before["description"])),
                "post_action_description_sha256": _sha256_text(str(readback["description"])),
                "protected_fields_sha256": readback["protected_hash"],
                "inventory_sha256": readback["inventory_hash"],
            }
        )
    return {
        "schema_version": 1,
        "mode": "exact_manifest_description_only",
        "manifest_sha256": plan["manifest_sha256"],
        "source_snapshot_sha256": plan["source_snapshot_sha256"],
        "external_account_writes": sum(item["status"] == "applied" for item in receipt_targets),
        "summary": {
            "applied": sum(item["status"] == "applied" for item in receipt_targets),
            "already_applied": sum(item["status"] == "already_applied" for item in receipt_targets),
        },
        "targets": receipt_targets,
    }


def _load_write_credentials() -> tuple[str, str]:
    def read(account: str) -> str:
        value = get_secret(account, source="etsy_env")
        if not value:
            raise ValueError(f"missing Etsy .etsy.env value: {account}")
        return value

    composite = read(API_CREDENTIAL_NAME)
    EtsyCredentials.from_composite(composite)
    access_token = read(ACCESS_TOKEN_NAME)
    expires_at = read(EXPIRES_AT_NAME)
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid Etsy OAuth expiry timestamp") from exc
    if expiry.tzinfo is None or expiry.astimezone(UTC) <= datetime.now(UTC):
        raise ValueError("Etsy OAuth token is expired; obtain fresh authorization before applying")
    return composite, access_token


def _write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"receipt path already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--approved-manifest-sha256", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirmed-exact-description-only-change", action="store_true")
    parser.add_argument("--receipt-output", type=Path)
    args = parser.parse_args(argv)
    try:
        plan = load_plan(args.manifest, approved_manifest_sha256=args.approved_manifest_sha256)
        if not args.apply:
            print(json.dumps({"prepared": True, "target_count": len(plan["targets"]), "external_account_writes": 0}))
            return 0
        if not args.confirmed_exact_description_only_change:
            raise ValueError("refusing to apply without action-time exact description-only confirmation")
        if args.receipt_output is None:
            raise ValueError("--receipt-output is required when applying")
        composite, access_token = _load_write_credentials()
        with EtsyDescriptionWriteClient(api_key=composite, access_token=access_token) as client:
            receipt = apply_plan(client, plan)
        _write_receipt(args.receipt_output, receipt)
    except (OSError, TypeError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"receipt": str(args.receipt_output), "summary": receipt["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
