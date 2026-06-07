#!/usr/bin/env python3
"""Check a client site's contact-form lead pipeline (the `hosting` SLA).

Reads lead records drained from the client's Netlify Blobs ``inbound-leads``
store and prints a health verdict. An ``alert`` status means leads are being
captured but the owner isn't being emailed (or the store is unreachable) — the
silent failure the $49/mo "contact-form monitoring" promise exists to catch.

Draining the Blobs store into ``--leads-dir`` is a separate Node step (mirrors
``scripts/web/pull-inbound.mjs``); this script assesses what was drained.

Exit code is the alert level: 0 ok, 1 warn, 2 alert — so a cron/launchd wrapper
can page on non-zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.lead_health import (  # noqa: E402
    LeadHealthStatus,
    assess_lead_health,
    load_leads_from_dir,
)

_EXIT = {LeadHealthStatus.OK: 0, LeadHealthStatus.WARN: 1, LeadHealthStatus.ALERT: 2}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-id", required=True)
    parser.add_argument(
        "--leads-dir", type=Path, required=True, help="dir of drained lead JSON files"
    )
    parser.add_argument("--as-of", required=True, help="reference date YYYY-MM-DD")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument(
        "--store-unreachable",
        action="store_true",
        help="the drain could not read the Blobs store",
    )
    args = parser.parse_args()

    leads = load_leads_from_dir(args.leads_dir)
    health = assess_lead_health(
        leads,
        product_id=args.product_id,
        as_of=date.fromisoformat(args.as_of),
        window_days=args.window_days,
        store_reachable=not args.store_unreachable,
    )
    print(json.dumps(health.to_dict(), indent=2))
    return _EXIT[health.status]


if __name__ == "__main__":
    raise SystemExit(main())
