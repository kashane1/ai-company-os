#!/usr/bin/env python3
"""Draft a Google Ads campaign (ADS.md) from client intake (G8).

Example:
  python scripts/agency/draft_google_ads.py --business "Joe's Plumbing" \\
    --service plumbing --city "Austin, TX" --services "Drain cleaning,Water heaters" \\
    --service-area "Austin,Round Rock" --daily-budget 25 --monthly-budget 600 \\
    --out docs/products/joes-plumbing-site
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.google_ads import draft_google_ads, emit_ads_draft  # noqa: E402
from packages.agency.intake import ClientIntake  # noqa: E402


def _csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--business", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--services", default="")
    parser.add_argument("--service-area", default="", help="comma-separated cities")
    parser.add_argument("--site-url", default="https://example.com")
    parser.add_argument("--daily-budget", type=float, default=None)
    parser.add_argument("--monthly-budget", type=float, default=None)
    parser.add_argument("--out", type=Path, help="client docs dir → writes ADS.md")
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args()

    intake = ClientIntake(
        business_name=args.business,
        service_category=args.service,
        city=args.city,
        services=_csv(args.services),
        service_area_cities=_csv(args.service_area),
        site_url=args.site_url,
    )

    try:
        if args.print or not args.out:
            draft = draft_google_ads(
                intake, daily_budget=args.daily_budget, monthly_budget=args.monthly_budget
            )
            sys.stdout.write(draft.to_markdown())
            return 0
        path = emit_ads_draft(
            intake, args.out, daily_budget=args.daily_budget, monthly_budget=args.monthly_budget
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"path": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
