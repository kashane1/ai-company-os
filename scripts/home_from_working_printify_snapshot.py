#!/usr/bin/env python3
"""Save a sanitized, read-only Printify inventory snapshot for reconciliation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.config.secrets import require_secret  # noqa: E402
from packages.pod.runner import PrintifyClient, save_json  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPO_ROOT / "state/home-from-working/operations/evidence"


def default_output_path(observed_at: str) -> Path:
    """Use the observation date rather than a stale, hard-coded evidence folder."""
    timestamp = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    return EVIDENCE_ROOT / timestamp.date().isoformat() / "printify-products.json"


def ensure_output_writable(output: Path, *, overwrite: bool) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {output}; pass --overwrite to replace it")


def sanitize_product(product: dict[str, Any]) -> dict[str, Any]:
    raw_external = product.get("external")
    external = (
        {
            key: raw_external[key]
            for key in ("id", "handle")
            if key in raw_external and raw_external[key] is not None
        }
        if isinstance(raw_external, dict)
        else {}
    )
    variants = [
        variant for variant in product.get("variants", []) if isinstance(variant, dict)
    ]
    enabled = [variant for variant in variants if variant.get("is_enabled") is True]
    variant_summary = {
        "total_count": len(variants),
        "enabled_count": len(enabled),
        "available_enabled_count": sum(
            variant.get("is_available") is True for variant in enabled
        ),
        "enabled_cost_cents": sorted(
            {variant["cost"] for variant in enabled if isinstance(variant.get("cost"), int)}
        ),
        "enabled_price_cents": sorted(
            {variant["price"] for variant in enabled if isinstance(variant.get("price"), int)}
        ),
    }
    return {
        key: product.get(key)
        for key in (
            "id",
            "title",
            "blueprint_id",
            "print_provider_id",
            "shop_id",
            "visible",
            "is_locked",
            "is_deleted",
            "created_at",
            "updated_at",
        )
    } | {"external": external, "variant_summary": variant_summary}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--generated-at")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    generated_at = (
        args.generated_at
        or datetime.now().astimezone().replace(microsecond=0).isoformat()
    )
    output = args.output or default_output_path(generated_at)
    ensure_output_writable(output, overwrite=args.overwrite)
    client = PrintifyClient(require_secret("PRINTIFY_API_TOKEN", source="keychain"))
    try:
        products = [sanitize_product(product) for product in client.iter_products()]
    finally:
        client.close()
    snapshot = {
        "schema_version": 1,
        "generated_at": generated_at,
        "shop_id": 28779955,
        "mode": "read_only",
        "data": products,
    }
    save_json(output, snapshot)
    print(f"saved {len(products)} sanitized products to {output} (account writes: 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
