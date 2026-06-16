#!/usr/bin/env python3
"""Inject a POS "Order Online" button into a client site file (idempotent).

The client takes orders + payment through their own POS merchant account; we wire
its hosted ordering page into the site. Square + Clover are freely supported;
Toast is gated (a Done-for-you Setup on Toast is a hard block — only a Connect
link against an existing Toast ordering page is allowed).

Example:
  python scripts/agency/inject_ordering.py --site-file products/joes-site/dist/index.html \\
    --platform square --ordering-url https://order.square.site/joes-coffee \\
    --base ordering_setup --product-id joes-coffee-site
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.ordering import (  # noqa: E402
    ALL_PLATFORMS,
    ORDERING_BASES,
    ORDERING_MODIFIERS,
    OrderingError,
    OrderingSetup,
    check_modifiers,
    check_platform_for_tier,
    inject_order_into_file,
    save_ordering_setup,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--site-file", type=Path, required=True)
    parser.add_argument("--platform", required=True, choices=ALL_PLATFORMS)
    parser.add_argument("--ordering-url", required=True)
    parser.add_argument(
        "--base",
        default="ordering_connect",
        choices=ORDERING_BASES,
        help="purchased pick-one base SKU (validated against the platform)",
    )
    parser.add_argument("--label", default="Order Online", help="button text")
    parser.add_argument("--product-id", default="", help="record the setup if given")
    parser.add_argument(
        "--modifier",
        action="append",
        default=[],
        choices=ORDERING_MODIFIERS,
        help="purchased ordering modifier (repeatable)",
    )
    args = parser.parse_args()

    # Fail fast (before touching the site) if the tier can't run on this platform,
    # and surface gated-but-deliverable combos (e.g. Toast Connect) as warnings.
    errors, warnings = check_platform_for_tier(args.platform, args.base)
    errors += check_modifiers(args.modifier)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    try:
        path = inject_order_into_file(
            args.site_file, args.platform, args.ordering_url, args.label
        )
    except OrderingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out: dict[str, object] = {
        "injected": str(path),
        "platform": args.platform,
        "base": args.base,
        "modifiers": args.modifier,
        "warnings": warnings,
    }
    if args.product_id:
        record = OrderingSetup(
            product_id=args.product_id,
            platform=args.platform,
            ordering_url=args.ordering_url,
            base=args.base,
            injected=True,
            completed_at=datetime.now(timezone.utc).isoformat(),
            managed="ordering_management" in args.modifier,
            modifiers=tuple(args.modifier),
        )
        out["record"] = str(save_ordering_setup(record))

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
