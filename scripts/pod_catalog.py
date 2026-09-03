#!/usr/bin/env python3
"""Build an offline index of HomeFromWorking Printify product snapshots."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFTS = DEFAULT_ROOT / "state/home-from-working/drafts"
DEFAULT_OUTPUT = DEFAULT_ROOT / "state/home-from-working/catalog"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _source(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _status(folder: Path, review: dict[str, Any], after: dict[str, Any], receipt: dict[str, Any]) -> tuple[str, str]:
    recovery = _read(folder.parent / "recovery-status.json")
    if recovery and str(recovery.get("status", "")).startswith("awaiting_"):
        ids = recovery.get("drafts", {})
        if folder.name in ids:
            return "unresolved", "Recovery notes say the saved draft target disappeared; retained snapshots are historical evidence."
    if receipt.get("status") in {"verified", "already_verified"} and after:
        return "saved_verified", "A verified receipt and post-save product snapshot are present."
    if receipt:
        return "receipt_unverified", f"Receipt status recorded as {receipt.get('status', 'unknown')!r}; no verified saved snapshot was established."
    if after:
        return "saved_snapshot", "A post-save product snapshot is present without a verified receipt."
    if review:
        return "prepared_only", "Review/copy data is saved, but no post-save product snapshot or verified receipt is present."
    return "missing", "No usable review snapshot was found."


def _record(review_path: Path, root: Path, drafts_root: Path) -> dict[str, Any]:
    folder = review_path.parent
    relative_parts = folder.relative_to(drafts_root).parts
    design = relative_parts[-2] if len(relative_parts) > 1 else relative_parts[-1]
    variant = relative_parts[-1] if len(relative_parts) > 1 else None
    review = _read(review_path)
    payload = review.get("payload") or {}
    after_path, receipt_path, copy_path = folder / "after.json", folder / "receipt.json", folder / "copy.json"
    after, receipt, copy = _read(after_path), _read(receipt_path), _read(copy_path)
    source_data = after or review
    saved_payload = {
        "title": source_data.get("title") or payload.get("title") or copy.get("title"),
        "description": source_data.get("description") or payload.get("description") or copy.get("description") or copy.get("intro"),
        "tags": source_data.get("tags") or payload.get("tags") or copy.get("tags") or [],
    }
    status, status_note = _status(folder, review, after, receipt)
    variants = after.get("variants") or []
    enabled = [v for v in variants if v.get("is_enabled")]
    prices = sorted({v["price"] / 100 for v in enabled if isinstance(v.get("price"), (int, float))})
    costs = sorted({v["cost"] / 100 for v in enabled if isinstance(v.get("cost"), (int, float))})
    placements = []
    for area in (after.get("print_areas") or payload.get("print_areas") or []):
        for placeholder in area.get("placeholders", []):
            images = []
            for image in placeholder.get("images", []):
                images.append({key: image[key] for key in ("id", "imageId", "x", "y", "scale", "angle") if key in image})
            if images:
                placements.append({
                    "position": placeholder.get("position"),
                    "decoration_method": placeholder.get("decoration_method"),
                    "images": images,
                })
    review_areas = payload.get("print_areas") or []
    placement = {"saved": placements}
    if review_areas:
        # Keep compact review metadata while omitting the repeated variant ID lists.
        placement["review"] = [{key: area[key] for key in area if key != "variant_ids"} for area in review_areas]
    product_id = receipt.get("product_id") or after.get("id") or review.get("draft_id")
    sources = {"review": _source(review_path, root)}
    for label, path in (("copy", copy_path), ("after", after_path), ("receipt", receipt_path)):
        if path.exists():
            sources[label] = _source(path, root)
    recovery_path = folder.parent / "recovery-status.json"
    if recovery_path.exists():
        sources["recovery"] = _source(recovery_path, root)
    record = {
        "key": "/".join(relative_parts),
        "design": design,
        "variant": variant,
        "status": status,
        "status_note": status_note,
        "product_id": product_id,
        "draft_id": review.get("draft_id"),
        "printify_url": receipt.get("url") or (f"https://printify.com/app/product-details/{product_id}" if status == "saved_verified" else None),
        "copy": saved_payload,
        "artwork": review.get("artwork", {}),
        "garment": {"blueprint_id": after.get("blueprint_id"), "template_id": review.get("template_id"), "print_provider_id": after.get("print_provider_id"), "variant_count": len(variants), "enabled_variant_count": len(enabled)},
        "placement": placement,
        "prices_usd": prices,
        "costs_usd": costs,
        "sources": sources,
    }
    return record


def build_catalog(drafts_root: Path = DEFAULT_DRAFTS, repo_root: Path | None = None) -> dict[str, Any]:
    drafts_root = Path(drafts_root)
    root = Path(repo_root) if repo_root else drafts_root.parents[2]
    records = [_record(path, root, drafts_root) for path in sorted(drafts_root.rglob("review.json"))]
    return {"schema_version": 1, "generated_from": _source(drafts_root, root), "records": records}


def render_index(catalog: dict[str, Any], index_dir: Path | None = None, repo_root: Path | None = None) -> str:
    records = catalog["records"]
    lines = ["# HomeFromWorking product catalog", "", "Offline index of saved draft snapshots. Status is the last recorded state; it does not assert current Etsy or Printify state.", "", f"{len(records)} records", ""]
    for record in records:
        title = record["copy"].get("title") or "(untitled)"
        status = record["status"]
        links = []
        for name, path in record["sources"].items():
            # INDEX.md lives beside catalog.json under state/home-from-working/catalog.
            if index_dir and repo_root:
                link = os.path.relpath(repo_root / path, index_dir)
            else:
                link = path
            links.append(f"[{name}]({link})")
        if record.get("printify_url"):
            links.append(f"[Printify]({record['printify_url']})")
        label = f"{record['design']} / {record['variant']}" if record.get("variant") else record["design"]
        lines += [f"## {label}", f"**{title}** — `{status}`", f"Sources: {' · '.join(links)}", ""]
    return "\n".join(lines)


def write_catalog(drafts_root: Path = DEFAULT_DRAFTS, output_dir: Path = DEFAULT_OUTPUT, repo_root: Path | None = None) -> dict[str, Any]:
    catalog = build_catalog(drafts_root, repo_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "catalog.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    root = Path(repo_root) if repo_root else Path(drafts_root).parents[2]
    (output_dir / "INDEX.md").write_text(render_index(catalog, output_dir, root))
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drafts", type=Path, default=DEFAULT_DRAFTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    catalog = write_catalog(args.drafts, args.output, DEFAULT_ROOT)
    print(f"wrote {len(catalog['records'])} records to {args.output}")


if __name__ == "__main__":
    main()
