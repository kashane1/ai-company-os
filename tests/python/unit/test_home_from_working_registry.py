from __future__ import annotations

import pytest

from packages.home_from_working.registry import build_registry, serialize_registry


def _catalog(*records: dict) -> dict:
    return {"schema_version": 1, "records": list(records)}


def _record(
    key: str = "science/lightning-1",
    product_id: str = "product-1",
    title: str = "Lightning shirt",
    artwork_hash: str = "hash-1",
    status: str = "saved_verified",
) -> dict:
    return {
        "key": key,
        "design": key.split("/")[0],
        "variant": key.split("/")[1],
        "product_id": product_id,
        "status": status,
        "copy": {"title": title},
        "artwork": {"sha256": artwork_hash},
    }


def test_identifier_precedence_over_artwork_match() -> None:
    registry = build_registry(
        _catalog(_record(), _record("science/lightning-2", "product-2", artwork_hash="hash-2")),
        printify_snapshot=[
            {
                "id": "product-1",
                "design_key": "science/lightning-2",
                "artwork_sha256": "hash-2",
                "title": "Lightning shirt",
            }
        ],
        generated_at="2026-09-06T00:00:00Z",
    )

    first, second = registry["records"]
    assert first["match"]["method"] == "printify_product_id"
    assert first["live"]["printify"]["state"] == "present"
    assert second["live"]["printify"]["state"] == "missing"


def test_title_only_candidate_is_never_auto_merged() -> None:
    registry = build_registry(
        _catalog(_record()),
        printify_snapshot=[{"id": "product-other", "title": "Lightning shirt"}],
        generated_at="2026-09-06T00:00:00Z",
    )

    assert len(registry["records"]) == 2
    local = next(record for record in registry["records"] if record["record_id"] == "science/lightning-1")
    orphan = next(record for record in registry["records"] if record["record_id"] == "printify:product-other")
    assert local["live"]["printify"]["state"] == "missing"
    assert orphan["match"]["method"] == "unmatched"
    assert "title_only_candidate:science/lightning-1" in orphan["discrepancies"]


def test_parallel_multi_product_receipts_are_retained_without_merging() -> None:
    registry = build_registry(
        _catalog(_record()),
        multi_product_receipts=[
            {"multi_product_listing_id": "group-2", "members": {"shirt": "product-1"}},
            {"multi_product_listing_id": "group-1", "members": {"shirt": "product-1"}},
        ],
        generated_at="2026-09-06T00:00:00Z",
    )

    record = registry["records"][0]
    assert record["relationships"]["multi_product_listings"] == ["group-1", "group-2"]
    assert "parallel_multi_product_receipts:group-1,group-2" in record["discrepancies"]


def test_missing_printify_product_and_unresolved_banana_are_precise() -> None:
    banana = _record(
        "banana-berries-20260902/banana-berries-1",
        "6a98ec418c9207769700b224",
        status="unresolved",
    )
    registry = build_registry(
        _catalog(banana), printify_snapshot=[], generated_at="2026-09-06T00:00:00Z"
    )

    record = registry["records"][0]
    assert record["live"]["printify"]["state"] == "confirmed_missing"
    assert record["next_action"] == "do_not_recreate_automatically"
    assert "historical_unresolved" in record["discrepancies"]


def test_etsy_only_records_are_preserved() -> None:
    registry = build_registry(
        _catalog(),
        etsy_snapshot=[{"listing_id": 123, "title": "Found Etsy listing"}],
        generated_at="2026-09-06T00:00:00Z",
    )

    assert registry["records"] == [
        {
            "discrepancies": ["etsy_only_record"],
            "live": {"etsy": {"id": "123", "state": "present"}, "printify": {"state": "unknown"}},
            "local": {"state": "absent"},
            "match": {"confidence": "none", "method": "unmatched"},
            "next_action": "review_unmatched_etsy_listing",
            "provenance": {"etsy": ["snapshot"], "local": [], "printify": []},
            "record_id": "etsy:123",
            "relationships": {"multi_product_listings": []},
        }
    ]


def test_explicit_printify_external_listing_link_is_not_left_marked_printify_only() -> None:
    registry = build_registry(
        _catalog(),
        printify_snapshot=[
            {"id": "printify-1", "external": {"id": "123"}},
        ],
        etsy_snapshot=[{"listing_id": 123}],
        generated_at="2026-09-06T00:00:00Z",
    )

    record = registry["records"][0]
    assert record["live"] == {
        "etsy": {"id": "123", "state": "present"},
        "printify": {"id": "printify-1", "state": "present"},
    }
    assert "printify_only_record" not in record["discrepancies"]


def test_serialization_is_deterministic() -> None:
    first = build_registry(
        _catalog(_record("b/two", "two"), _record("a/one", "one")),
        generated_at="2026-09-06T00:00:00Z",
    )
    second = build_registry(
        _catalog(_record("a/one", "one"), _record("b/two", "two")),
        generated_at="2026-09-06T00:00:00Z",
    )
    assert serialize_registry(first) == serialize_registry(second)


def test_duplicate_local_product_id_is_ambiguous_and_never_auto_matches() -> None:
    registry = build_registry(
        _catalog(
            _record("science/one", "duplicated", artwork_hash="hash-one"),
            _record("science/two", "duplicated", artwork_hash="hash-two"),
        ),
        printify_snapshot=[{"id": "duplicated", "title": "Live product"}],
        generated_at="2026-09-06T00:00:00Z",
    )

    locals_ = [record for record in registry["records"] if record["local"]["state"] == "historical"]
    assert all(record["match"]["method"] == "ambiguous_local_identifier" for record in locals_)
    assert all(record["live"]["printify"]["state"] == "missing" for record in locals_)
    assert all(record["next_action"] == "resolve_local_identifier_collision" for record in locals_)
    orphan = next(record for record in registry["records"] if record["record_id"] == "printify:duplicated")
    assert orphan["match"]["method"] == "ambiguous_local_product_id"
    assert orphan["next_action"] == "resolve_local_identifier_collision"


def test_duplicate_design_and_artwork_identifier_is_ambiguous_and_never_auto_matches() -> None:
    registry = build_registry(
        _catalog(
            _record("science/one", "one", artwork_hash="same-hash"),
            _record("science/two", "two", artwork_hash="same-hash"),
        ),
        printify_snapshot=[
            {"id": "live-product", "design_key": "science", "artwork_sha256": "same-hash"}
        ],
        generated_at="2026-09-06T00:00:00Z",
    )

    locals_ = [record for record in registry["records"] if record["local"]["state"] == "historical"]
    assert all(record["match"]["method"] == "ambiguous_local_identifier" for record in locals_)
    assert all(record["live"]["printify"]["state"] == "missing" for record in locals_)
    orphan = next(record for record in registry["records"] if record["record_id"] == "printify:live-product")
    assert orphan["match"]["method"] == "ambiguous_local_design_and_artwork"
    assert orphan["next_action"] == "resolve_local_identifier_collision"


@pytest.mark.parametrize(
    ("snapshot", "entry_number"),
    [
        (["not-an-object"], 1),
        ({"data": [{"id": "valid"}, ["not-an-object"]]}, 2),
    ],
)
def test_non_object_printify_snapshot_entry_fails_closed(snapshot: object, entry_number: int) -> None:
    with pytest.raises(ValueError, match=f"Printify snapshot entry {entry_number} must be an object"):
        build_registry(_catalog(), printify_snapshot=snapshot, generated_at="2026-09-06T00:00:00Z")


def test_duplicate_printify_external_listing_id_fails_closed() -> None:
    with pytest.raises(ValueError, match="duplicate Printify external listing id: etsy-123"):
        build_registry(
            _catalog(),
            printify_snapshot=[
                {"id": "printify-one", "external": {"id": "etsy-123"}},
                {"id": "printify-two", "external": {"id": "etsy-123"}},
            ],
            generated_at="2026-09-06T00:00:00Z",
        )


def test_duplicate_catalog_key_fails_closed_before_registry_overwrite() -> None:
    with pytest.raises(ValueError, match="duplicate local catalog key: science/lightning-1"):
        build_registry(
            _catalog(_record(), _record(title="Different shirt", artwork_hash="different-hash")),
            generated_at="2026-09-06T00:00:00Z",
        )


@pytest.mark.parametrize(
    ("catalog_key", "printify_snapshot", "etsy_snapshot"),
    [
        ("printify:p1", [{"id": "p1"}], None),
        ("etsy:123", None, [{"listing_id": 123}]),
    ],
)
def test_synthetic_registry_id_cannot_overwrite_local_catalog_record(
    catalog_key: str,
    printify_snapshot: object | None,
    etsy_snapshot: object | None,
) -> None:
    with pytest.raises(
        ValueError,
        match=f"synthetic registry id collides with local catalog key: {catalog_key}",
    ):
        build_registry(
            _catalog({"key": catalog_key}),
            printify_snapshot=printify_snapshot,
            etsy_snapshot=etsy_snapshot,
            generated_at="2026-09-06T00:00:00Z",
        )


@pytest.mark.parametrize("bad_record", ["not-an-object", {}, {"key": "  "}])
def test_malformed_catalog_record_fails_closed(bad_record: object) -> None:
    with pytest.raises(ValueError, match="catalog record 1"):
        build_registry(
            {"schema_version": 1, "records": [bad_record]},
            generated_at="2026-09-06T00:00:00Z",
        )


def test_duplicate_or_missing_etsy_listing_ids_fail_closed() -> None:
    with pytest.raises(ValueError, match="no listing id"):
        build_registry(
            _catalog(),
            etsy_snapshot=[{"title": "No ID"}],
            generated_at="2026-09-06T00:00:00Z",
        )
    with pytest.raises(ValueError, match="duplicate Etsy listing id: 123"):
        build_registry(
            _catalog(),
            etsy_snapshot=[{"listing_id": 123}, {"listing_id": 123}],
            generated_at="2026-09-06T00:00:00Z",
        )


@pytest.mark.parametrize(
    "receipt",
    [
        "not-an-object",
        {},
        {"multi_product_listing_id": "group-1"},
        {"multi_product_listing_id": "group-1", "members": {}},
        {"multi_product_listing_id": "group-1", "members": {"shirt": "  "}},
    ],
)
def test_malformed_multi_product_receipt_fails_closed(receipt: object) -> None:
    with pytest.raises(ValueError, match="multi-product receipt 1"):
        build_registry(
            _catalog(_record()),
            multi_product_receipts=[receipt],  # type: ignore[list-item]
            generated_at="2026-09-06T00:00:00Z",
        )
