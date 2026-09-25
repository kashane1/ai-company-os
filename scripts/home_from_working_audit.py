#!/usr/bin/env python3
"""Create local-only, deterministic trust and production-master asset audits."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.home_from_working.assets import AssetStandard, inspect_asset  # noqa: E402
from packages.home_from_working.trust import (  # noqa: E402
    audit_listing_trust,
    derive_live_etsy_trust,
)


DEFAULT_CATALOG = Path("state/home-from-working/catalog/catalog.json")
DEFAULT_REGISTRY = Path("state/home-from-working/operations/registry.json")
DEFAULT_TRUST_OUTPUT = Path("state/home-from-working/operations/trust-audit.json")
DEFAULT_ASSET_OUTPUT = Path("state/home-from-working/operations/asset-audit.json")


def _records(document: Mapping[str, object]) -> list[dict[str, Any]]:
    records = document.get("records", [])
    if not isinstance(records, list):
        raise ValueError("document records must be a list")
    return [
        record for record in records if isinstance(record, dict) and record.get("key")
    ]


def _registry_etsy_states(registry: Mapping[str, object]) -> dict[str, str]:
    records = registry.get("records", [])
    if not isinstance(records, list):
        raise ValueError("registry records must be a list")
    states: dict[str, str] = {}
    for record in records:
        if not isinstance(record, Mapping):
            continue
        key = record.get("record_id")
        live = record.get("live")
        etsy = live.get("etsy") if isinstance(live, Mapping) else None
        state = etsy.get("state") if isinstance(etsy, Mapping) else None
        if key is not None:
            states[str(key)] = str(state) if state is not None else "unknown"
    return states


def _registry_records(registry: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    records = registry.get("records", [])
    if not isinstance(records, list):
        raise ValueError("registry records must be a list")
    return {
        str(record["record_id"]): record
        for record in records
        if isinstance(record, Mapping) and record.get("record_id") is not None
    }


def _snapshot_items(
    snapshot: Mapping[str, object], name: str
) -> list[Mapping[str, object]]:
    items = snapshot.get(name)
    if not isinstance(items, list) or any(not isinstance(item, Mapping) for item in items):
        raise ValueError(f"Etsy snapshot {name} must be a list of objects")
    return list(items)


def _summary(records: list[dict[str, object]], *, field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(record[field]) for record in records).items()))


def _asset_standard_document(standard: AssetStandard) -> dict[str, object]:
    """Use integer-friendly values in the persisted standard, not float math."""

    return {
        "format": "PNG",
        "transparency_required": True,
        "minimum_width_px": standard.min_width,
        "minimum_height_px": standard.min_height,
        "print_width_inches": int(standard.print_width_inches),
        "minimum_effective_dpi": int(standard.min_effective_dpi),
        "maximum_edge_padding_basis_points": int(standard.max_edge_padding_ratio * 10_000),
    }


def _asset_path(raw_path: object, workspace: Path) -> Path:
    path = Path(str(raw_path))
    return path if path.is_absolute() else workspace / path


def build_audits(
    catalog: Mapping[str, object],
    registry: Mapping[str, object],
    *,
    workspace: Path,
    etsy_snapshot: Mapping[str, object] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    """Inspect supplied local evidence only; this function has no external side effects."""

    standard = AssetStandard()
    etsy_states = _registry_etsy_states(registry)
    registry_records = _registry_records(registry)
    listings: dict[str, Mapping[str, object]] = {}
    shipping_profiles: list[Mapping[str, object]] = []
    production_partners: list[Mapping[str, object]] = []
    if etsy_snapshot is not None:
        listing_items = _snapshot_items(etsy_snapshot, "listings")
        shipping_profiles = _snapshot_items(etsy_snapshot, "shipping_profiles")
        production_partners = _snapshot_items(etsy_snapshot, "production_partners")
        for listing in listing_items:
            listing_id = listing.get("listing_id")
            if listing_id is None:
                raise ValueError("Etsy snapshot listing is missing listing_id")
            key = str(listing_id)
            if key in listings:
                raise ValueError(f"duplicate Etsy snapshot listing_id: {key}")
            listings[key] = listing
    trust_records: list[dict[str, object]] = []
    asset_records: list[dict[str, object]] = []
    for record in sorted(_records(catalog), key=lambda item: str(item["key"])):
        key = str(record["key"])
        registry_record = registry_records.get(key, {})
        live = registry_record.get("live") if isinstance(registry_record, Mapping) else None
        live_etsy = live.get("etsy") if isinstance(live, Mapping) else None
        listing_id = live_etsy.get("id") if isinstance(live_etsy, Mapping) else None
        listing = listings.get(str(listing_id)) if listing_id is not None else None
        if listing is not None:
            enriched = dict(record)
            enriched["etsy"] = derive_live_etsy_trust(
                listing,
                shipping_profiles=shipping_profiles,
                production_partners=production_partners,
            )
            trust = audit_listing_trust(enriched)
            evidence_source = "live_etsy_snapshot"
        else:
            # Catalog fields are planning data, not proof that Etsy currently
            # displays the disclosure or policy. Never let them turn a trust
            # audit green without the exact registry-to-snapshot ID match.
            trust = audit_listing_trust({"key": key, "etsy": {}})
            if listing_id is not None and etsy_snapshot is not None:
                evidence_source = "registry_listing_missing_from_snapshot"
            elif listing_id is not None:
                evidence_source = "live_etsy_snapshot_not_supplied"
            else:
                evidence_source = "catalog_only"
        trust_records.append({
            **trust,
            "registry_etsy_state": etsy_states.get(key, "unknown"),
            "evidence_source": evidence_source,
        })

        artwork = record.get("artwork")
        artwork_fields = artwork if isinstance(artwork, Mapping) else {}
        raw_path = artwork_fields.get("path")
        recorded_sha256 = artwork_fields.get("sha256")
        hero = record.get("hero_image", record.get("hero_manifest"))
        hero_manifest = hero if isinstance(hero, Mapping) else None
        if raw_path is None or not str(raw_path).strip():
            inspection: dict[str, object] = {
                "path": None,
                "status": "blocked_missing_file",
                "checks": {},
                "hash_integrity_check": "blocked_missing_file",
                "hero_image_check": (
                    "not_applicable_no_manifest" if hero_manifest is None else "blocked_missing_file"
                ),
                "error": "catalog artwork path is missing",
            }
        else:
            inspection = inspect_asset(
                _asset_path(raw_path, workspace),
                standard,
                hero_manifest=hero_manifest,
                recorded_sha256=(
                    str(recorded_sha256) if recorded_sha256 is not None else None
                ),
            )
        status = str(inspection["status"])
        if recorded_sha256 is None and status == "pass":
            status = "blocked_missing_hash"
        asset_records.append({
            "key": key,
            "recorded_artwork_path": raw_path,
            "recorded_sha256": recorded_sha256,
            "status": status,
            "inspection": inspection,
        })

    trust_audit: dict[str, object] = {
        "schema_version": 1,
        "read_only": True,
        "generated_from": [
            "catalog/catalog.json",
            "operations/registry.json",
            *(["Etsy snapshot supplied to command"] if etsy_snapshot is not None else []),
        ],
        "summary": _summary(trust_records, field="overall"),
        "records": trust_records,
    }
    asset_audit: dict[str, object] = {
        "schema_version": 1,
        "read_only": True,
        "generated_from": ["catalog/catalog.json"],
        "production_master_standard": _asset_standard_document(standard),
        "summary": _summary(asset_records, field="status"),
        "records": asset_records,
    }
    return trust_audit, asset_audit


def _load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return document


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--trust-output", type=Path, default=DEFAULT_TRUST_OUTPUT)
    parser.add_argument("--asset-output", type=Path, default=DEFAULT_ASSET_OUTPUT)
    parser.add_argument(
        "--etsy-snapshot",
        type=Path,
        help="sanitized Etsy snapshot whose listing IDs have been reconciled into the registry",
    )
    parser.add_argument(
        "--check", action="store_true", help="validate only; do not write artifacts"
    )
    args = parser.parse_args()
    try:
        trust_audit, asset_audit = build_audits(
            _load_json(args.catalog),
            _load_json(args.registry),
            workspace=Path.cwd(),
            etsy_snapshot=_load_json(args.etsy_snapshot) if args.etsy_snapshot else None,
        )
        if not args.check:
            _write_json(args.trust_output, trust_audit)
            _write_json(args.asset_output, asset_audit)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 1
    print(
        "read-only audit: "
        f"trust={trust_audit['summary']}; assets={asset_audit['summary']}; "
        f"artifact_writes={0 if args.check else 2}; external_mutations=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
