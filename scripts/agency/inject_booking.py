#!/usr/bin/env python3
"""Inject a booking provider's embed into a client site file (idempotent) — G6.

Example:
  python scripts/agency/inject_booking.py --site-file products/joes-site/dist/index.html \\
    --provider calendly --booking-url https://calendly.com/joes-plumbing \\
    --product-id joes-plumbing-site
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.booking import (  # noqa: E402
    BOOKING_MODIFIERS,
    SUPPORTED_PROVIDERS,
    BookingError,
    BookingSetup,
    check_modifiers_for_platform,
    inject_booking_into_file,
    save_booking_setup,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--site-file", type=Path, required=True)
    parser.add_argument("--provider", required=True, choices=SUPPORTED_PROVIDERS)
    parser.add_argument("--booking-url", required=True)
    parser.add_argument("--product-id", default="", help="record the setup if given")
    parser.add_argument(
        "--modifier",
        action="append",
        default=[],
        choices=BOOKING_MODIFIERS,
        help="purchased booking modifier (repeatable) — validated against the provider",
    )
    args = parser.parse_args()

    # Fail fast (before touching the site) if a modifier can't run on this platform,
    # and surface degraded-but-deliverable combos as warnings.
    errors, warnings = check_modifiers_for_platform(args.provider, args.modifier)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    try:
        path = inject_booking_into_file(args.site_file, args.provider, args.booking_url)
    except BookingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out: dict[str, object] = {
        "injected": str(path),
        "provider": args.provider,
        "modifiers": args.modifier,
        "warnings": warnings,
    }
    if args.product_id:
        record = BookingSetup(
            product_id=args.product_id,
            provider=args.provider,
            booking_url=args.booking_url,
            injected=True,
            completed_at=datetime.now(timezone.utc).isoformat(),
            modifiers=tuple(args.modifier),
        )
        out["record"] = str(save_booking_setup(record))

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
