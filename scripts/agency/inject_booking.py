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
    SUPPORTED_PROVIDERS,
    BookingError,
    BookingSetup,
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
    args = parser.parse_args()

    try:
        path = inject_booking_into_file(args.site_file, args.provider, args.booking_url)
    except BookingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out: dict[str, object] = {"injected": str(path), "provider": args.provider}
    if args.product_id:
        record = BookingSetup(
            product_id=args.product_id,
            provider=args.provider,
            booking_url=args.booking_url,
            injected=True,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        out["record"] = str(save_booking_setup(record))

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
