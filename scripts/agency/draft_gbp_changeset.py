#!/usr/bin/env python3
"""Draft a GBP_CHANGESET.md from client intake (G7).

Example:
  python scripts/agency/draft_gbp_changeset.py --business "Joe's Plumbing" \\
    --service plumbing --city "Austin, TX" --services "Drain cleaning,Water heaters" \\
    --hours "Mon-Fri 8-6" --phone "512-555-0100" --booking-url https://book.example.com \\
    --out docs/products/joes-plumbing-site
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.gbp import draft_gbp_changeset, emit_gbp_changeset  # noqa: E402
from packages.agency.intake import ClientIntake  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--business", required=True)
    parser.add_argument("--service", required=True, help="service category, e.g. plumbing")
    parser.add_argument("--city", required=True)
    parser.add_argument("--services", default="", help="comma-separated service list")
    parser.add_argument("--hours", default="")
    parser.add_argument("--phone", default="")
    parser.add_argument("--site-url", default="https://example.com")
    parser.add_argument("--booking-url", default="")
    parser.add_argument("--out", type=Path, help="client docs dir → writes GBP_CHANGESET.md")
    parser.add_argument("--print", action="store_true", help="print markdown to stdout instead")
    args = parser.parse_args()

    services = [s.strip() for s in args.services.split(",") if s.strip()]
    intake = ClientIntake(
        business_name=args.business,
        service_category=args.service,
        city=args.city,
        services=services,
        hours=args.hours,
        phone=args.phone,
        site_url=args.site_url,
    )

    try:
        if args.print or not args.out:
            changeset = draft_gbp_changeset(intake, booking_url=args.booking_url)
            sys.stdout.write(changeset.to_markdown())
            return 0
        path = emit_gbp_changeset(intake, args.out, booking_url=args.booking_url)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"path": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
