#!/usr/bin/env python3
"""Create a derived, offline HomeFromWorking reconciliation registry.

The command only reads local JSON snapshots and writes derived local artifacts.
It never contacts Printify or Etsy and cannot publish, update, duplicate, or
delete a product/listing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.home_from_working.reconcile import build_reconciliation_report
from packages.home_from_working.registry import build_registry, serialize_registry

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = REPO_ROOT / "state/home-from-working/catalog/catalog.json"
DEFAULT_RECEIPT_ROOTS = (
    REPO_ROOT / "state/home-from-working/multi-product-listings",
    REPO_ROOT / "state/home-from-working/multi-product-listings-10color",
)
DEFAULT_REGISTRY = REPO_ROOT / "state/home-from-working/operations/registry.json"
DEFAULT_REPORT = REPO_ROOT / "state/home-from-working/operations/reconciliation-report.json"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def receipt_paths(roots: list[Path] | tuple[Path, ...]) -> list[Path]:
    """Discover only direct saved-draft receipts in explicitly named MPL roots."""
    paths: set[Path] = set()
    for root in roots:
        if root.exists():
            paths.update(path.resolve() for path in root.glob("*/saved-draft-evidence.json"))
    return sorted(paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument(
        "--receipts-root",
        type=Path,
        action="append",
        help=(
            "Explicit MPL root; repeat to combine roots. Defaults to the two known "
            "multi-product receipt directories."
        ),
    )
    parser.add_argument("--printify-snapshot", type=Path)
    parser.add_argument("--etsy-snapshot", type=Path)
    parser.add_argument("--registry-output", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--generated-at",
        help="RFC 3339 timestamp; pass this for reproducible artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated_at = args.generated_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt_roots = tuple(args.receipts_root) if args.receipts_root else DEFAULT_RECEIPT_ROOTS
    receipt_files = receipt_paths(receipt_roots)
    registry = build_registry(
        _load_json(args.catalog),
        printify_snapshot=_load_json(args.printify_snapshot) if args.printify_snapshot else None,
        etsy_snapshot=_load_json(args.etsy_snapshot) if args.etsy_snapshot else None,
        multi_product_receipts=[_load_json(path) for path in receipt_files],
        generated_at=generated_at,
    )
    report = build_reconciliation_report(registry)
    for path, payload in ((args.registry_output, registry), (args.report_output, report)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialize_registry(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "registry": str(args.registry_output),
                "report": str(args.report_output),
                "receipt_count": len(receipt_files),
                "mode": "offline_read_only",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
