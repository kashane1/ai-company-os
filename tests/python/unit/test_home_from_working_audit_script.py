"""Tests for the local-only HomeFromWorking trust and asset audit command."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw


def _module():
    path = Path("scripts/home_from_working_audit.py")
    spec = importlib.util.spec_from_file_location("home_from_working_audit", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_audits_marks_unknown_trust_and_missing_artwork_without_guessing(
    tmp_path: Path,
) -> None:
    audit = _module()
    catalog = {
        "records": [
            {
                "key": "design/variant",
                "artwork": {"path": "not-present.png", "sha256": "expected-hash"},
                "etsy": {"production_partner_disclosed": True},
            }
        ]
    }
    registry = {
        "records": [
            {"record_id": "design/variant", "live": {"etsy": {"state": "unknown"}}}
        ]
    }

    trust, assets = audit.build_audits(catalog, registry, workspace=tmp_path)

    assert trust["read_only"] is True
    assert trust["records"][0]["overall"] == "blocked_unknown"
    assert trust["records"][0]["registry_etsy_state"] == "unknown"
    assert assets["production_master_standard"]["format"] == "PNG"
    assert assets["records"][0]["status"] == "blocked_missing_file"
    assert assets["records"][0]["recorded_sha256"] == "expected-hash"
    assert assets["summary"] == {"blocked_missing_file": 1}


def test_build_audits_is_key_sorted_and_deterministic(tmp_path: Path) -> None:
    audit = _module()
    catalog = {
        "records": [
            {"key": "z/2", "artwork": {"path": "z.png"}},
            {"key": "a/1", "artwork": {"path": "a.png"}},
        ]
    }

    first = audit.build_audits(catalog, {"records": []}, workspace=tmp_path)
    second = audit.build_audits(catalog, {"records": []}, workspace=tmp_path)

    assert first == second
    assert [record["key"] for record in first[0]["records"]] == ["a/1", "z/2"]


def test_build_audits_enforces_catalog_hash_and_ai_hero_manifest(tmp_path: Path) -> None:
    audit = _module()
    path = tmp_path / "master.png"
    image = Image.new("RGBA", (2400, 2400), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((600, 600, 1800, 1800), fill=(255, 0, 0, 255))
    image.save(path)
    catalog = {
        "records": [
            {
                "key": "design/variant",
                "artwork": {"path": str(path), "sha256": "0" * 64},
                "hero_image": {"source": "ai", "illustrative_mockup": False},
            }
        ]
    }

    _, assets = audit.build_audits(catalog, {"records": []}, workspace=tmp_path)

    record = assets["records"][0]
    assert record["status"] == "fail"
    assert record["inspection"]["checks"]["hash_integrity"] == "fail"
    assert record["inspection"]["hero_image_check"] == "fail_misrepresentation_risk"


def test_build_audits_uses_live_etsy_snapshot_by_registry_listing_id(
    tmp_path: Path,
) -> None:
    audit = _module()
    catalog = {"records": [{"key": "design/variant", "artwork": {}}]}
    registry = {
        "records": [
            {
                "record_id": "design/variant",
                "live": {"etsy": {"state": "present", "id": "42"}},
            }
        ]
    }
    snapshot = {
        "listings": [
            {
                "listing_id": 42,
                "description": (
                    "FIT AND SIZING and size chart. AI-assisted tools were used."
                ),
                "shipping_profile_id": 7,
                "return_policy_id": 8,
                "production_partner_ids": [4],
                "inventory": [
                    {"property_values": [{"property_name": "Size"}]}
                ],
            }
        ],
        "shipping_profiles": [
            {
                "shipping_profile_id": 7,
                "origin_country_iso": "US",
                "processing_min": 2,
                "processing_max": 5,
                "destinations": [],
            }
        ],
        "production_partners": [
            {"production_partner_id": 4, "is_active": True, "is_deleted": False}
        ],
    }

    trust, _ = audit.build_audits(
        catalog,
        registry,
        workspace=tmp_path,
        etsy_snapshot=snapshot,
    )

    assert trust["records"][0]["overall"] == "pass"
    assert trust["records"][0]["evidence_source"] == "live_etsy_snapshot"


def test_build_audits_keeps_absent_live_fields_unknown_but_reports_missing_ai_copy(
    tmp_path: Path,
) -> None:
    audit = _module()
    catalog = {"records": [{"key": "design/variant", "artwork": {}}]}
    registry = {
        "records": [
            {
                "record_id": "design/variant",
                "live": {"etsy": {"state": "present", "id": "42"}},
            }
        ]
    }
    snapshot = {
        "listings": [
            {
                "listing_id": 42,
                "description": "FIT AND SIZING. Use the size chart.",
                "shipping_profile_id": 7,
                "return_policy_id": 8,
                "inventory": [
                    {
                        "property_values": [
                            {"property_id": 513, "property_name": "Clothing sizes"}
                        ]
                    }
                ],
            }
        ],
        "shipping_profiles": [
            {"shipping_profile_id": 7, "origin_country_iso": "US", "destinations": []}
        ],
        "production_partners": [{"production_partner_id": 4}],
    }

    trust, _ = audit.build_audits(
        catalog,
        registry,
        workspace=tmp_path,
        etsy_snapshot=snapshot,
    )

    record = trust["records"][0]
    assert record["overall"] == "fail"
    assert record["checks"] == {
        "ai_disclosure": "fail",
        "processing_policy": "unknown",
        "production_partner": "unknown",
        "returns_policy": "pass",
        "shipping_origin": "pass",
        "size_information": "pass",
    }


def test_build_audits_does_not_title_match_unlinked_etsy_listing(tmp_path: Path) -> None:
    audit = _module()
    catalog = {
        "records": [
            {
                "key": "design/variant",
                "copy": {"title": "Same title"},
                "artwork": {},
            }
        ]
    }
    snapshot = {
        "listings": [{"listing_id": 42, "title": "Same title"}],
        "shipping_profiles": [],
        "production_partners": [],
    }

    trust, _ = audit.build_audits(
        catalog,
        {"records": []},
        workspace=tmp_path,
        etsy_snapshot=snapshot,
    )

    assert trust["records"][0]["overall"] == "blocked_unknown"
    assert trust["records"][0]["evidence_source"] == "catalog_only"


def test_build_audits_blocks_catalog_only_claims_even_when_they_are_complete(
    tmp_path: Path,
) -> None:
    audit = _module()
    catalog = {
        "records": [
            {
                "key": "design/variant",
                "artwork": {},
                "etsy": {
                    "production_partner_disclosed": True,
                    "ai_disclosure_complete": True,
                    "shipping_origin_verified": True,
                    "processing_policy_complete": True,
                    "returns_policy_complete": True,
                    "size_information_complete": True,
                },
            }
        ]
    }

    trust, _ = audit.build_audits(catalog, {"records": []}, workspace=tmp_path)

    record = trust["records"][0]
    assert record["overall"] == "blocked_unknown"
    assert set(record["checks"].values()) == {"unknown"}
    assert record["evidence_source"] == "catalog_only"


def test_build_audits_blocks_registry_listing_missing_from_live_snapshot(
    tmp_path: Path,
) -> None:
    audit = _module()
    catalog = {
        "records": [
            {
                "key": "design/variant",
                "artwork": {},
                "etsy": {
                    "production_partner_disclosed": True,
                    "ai_disclosure_complete": True,
                    "shipping_origin_verified": True,
                    "processing_policy_complete": True,
                    "returns_policy_complete": True,
                    "size_information_complete": True,
                },
            }
        ]
    }
    registry = {
        "records": [
            {
                "record_id": "design/variant",
                "live": {"etsy": {"state": "present", "id": "42"}},
            }
        ]
    }
    snapshot = {
        "listings": [],
        "shipping_profiles": [],
        "production_partners": [],
    }

    trust, _ = audit.build_audits(
        catalog,
        registry,
        workspace=tmp_path,
        etsy_snapshot=snapshot,
    )

    record = trust["records"][0]
    assert record["overall"] == "blocked_unknown"
    assert set(record["checks"].values()) == {"unknown"}
    assert record["evidence_source"] == "registry_listing_missing_from_snapshot"
