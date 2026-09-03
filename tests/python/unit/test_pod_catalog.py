import json
from pathlib import Path

from scripts.pod_catalog import build_catalog, render_index, write_catalog


def _review(folder: Path, title: str, description: str = "FULL DESCRIPTION") -> None:
    folder.mkdir(parents=True)
    (folder / "review.json").write_text(json.dumps({"draft_id": "draft-1", "template_id": "template", "artwork": {"path": "/tmp/art.png"}, "payload": {"title": title, "description": description, "tags": ["one", "two"]}}))


def test_catalog_distinguishes_verified_prepared_and_error(tmp_path):
    _review(tmp_path / "good" / "v1", "Good")
    (tmp_path / "good" / "v1" / "after.json").write_text(json.dumps({"id": "product-1", "title": "Good", "description": "FULL DESCRIPTION", "tags": ["one", "two"], "variants": [{"price": 1799, "cost": 740, "is_enabled": True}], "blueprint_id": 6, "print_provider_id": 99}))
    (tmp_path / "good" / "v1" / "receipt.json").write_text(json.dumps({"status": "verified", "product_id": "product-1", "url": "https://printify.com/app/product-details/product-1"}))
    _review(tmp_path / "pending" / "v1", "Pending")
    _review(tmp_path / "failed" / "v1", "Failed")
    (tmp_path / "failed" / "v1" / "receipt.json").write_text(json.dumps({"status": "error", "message": "404"}))
    by_design = {r["design"]: r for r in build_catalog(tmp_path, tmp_path)["records"]}
    records = by_design["good"], by_design["pending"], by_design["failed"]
    assert [r["status"] for r in records] == ["saved_verified", "prepared_only", "receipt_unverified"]


def test_already_verified_receipt_is_success_and_preserves_placement(tmp_path):
    folder = tmp_path / "good" / "v1"
    _review(folder, "Good")
    (folder / "after.json").write_text(json.dumps({"id": "product-1", "title": "Good", "description": "FULL DESCRIPTION", "tags": [], "print_areas": [{"placeholders": [{"position": "front", "decoration_method": "dtg", "images": [{"id": "image-1", "x": 0.5, "y": 0.4, "scale": 0.6, "angle": 2, "variant_ids": [1, 2]}]}]}], "variants": []}))
    (folder / "receipt.json").write_text(json.dumps({"status": "already_verified", "product_id": "product-1"}))
    record = build_catalog(tmp_path, tmp_path)["records"][0]
    assert record["status"] == "saved_verified"
    assert record["placement"]["saved"][0]["images"][0] == {"id": "image-1", "x": 0.5, "y": 0.4, "scale": 0.6, "angle": 2}


def test_catalog_retains_full_copy_and_writes_index(tmp_path):
    folder = tmp_path / "design" / "v1"
    _review(folder, "Title", "line one\n\nline two")
    (folder / "copy.json").write_text(json.dumps({"tags": ["one", "two", "three"]}))
    output = tmp_path / "catalog"
    catalog = write_catalog(tmp_path, output, tmp_path)
    record = catalog["records"][0]
    assert record["copy"]["description"] == "line one\n\nline two"
    assert record["copy"]["tags"] == ["one", "two"]
    assert "line one" not in (output / "INDEX.md").read_text()
    assert "../design/v1/review.json" in (output / "INDEX.md").read_text()
    assert (output / "catalog.json").exists()
