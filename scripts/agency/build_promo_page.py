#!/usr/bin/env python3
"""Build a single-offer promotional landing page (G4).

Example:
  python scripts/agency/build_promo_page.py --business "Joe's Plumbing" \\
    --headline "20% off your first drain cleaning" --city "Austin, TX" \\
    --expiry "Offer ends June 30" --out state/agency/promos/joes-summer
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.promo_page import PromoCampaign, emit_promo_page  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--business", required=True)
    parser.add_argument("--headline", required=True, help="the one offer the page sells")
    parser.add_argument("--detail", default="")
    parser.add_argument("--cta", default="Claim this offer")
    parser.add_argument("--city", default="")
    parser.add_argument("--service", default="")
    parser.add_argument("--expiry", default="", help="urgency note, e.g. 'Offer ends June 30'")
    parser.add_argument("--site-url", default="https://example.com")
    parser.add_argument("--out", type=Path, required=True, help="output dir → dist/index.html")
    args = parser.parse_args()

    campaign = PromoCampaign(
        business_name=args.business,
        offer_headline=args.headline,
        offer_detail=args.detail,
        cta_label=args.cta,
        city=args.city,
        service_category=args.service,
        expiry=args.expiry,
        site_url=args.site_url,
    )
    try:
        path = emit_promo_page(campaign, args.out)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"path": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
