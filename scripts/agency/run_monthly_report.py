#!/usr/bin/env python3
"""Render a draft monthly report for a client site."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.client_lifecycle import client_paths  # noqa: E402
from packages.agency.monthly_report import (  # noqa: E402
    MonthlyMetrics,
    load_monthly_metrics,
    metrics_from_plausible,
    write_monthly_report,
)
from packages.agency.plausible import default_stats_client  # noqa: E402
from packages.agency.registry import get_registry_record  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--month", required=True, help="YYYY-MM")
    parser.add_argument("--metrics-json", type=Path)
    parser.add_argument("--site-id", help="Plausible site_id — pull real visits/leads (G10)")
    parser.add_argument("--visits", type=int, default=0)
    parser.add_argument("--form-leads", type=int, default=0)
    parser.add_argument("--completed-work", action="append", default=[])
    parser.add_argument("--recommended-action", default="")
    parser.add_argument(
        "--bookings",
        type=int,
        default=None,
        help="bookings this month from the managed-booking dashboard (omit if N/A)",
    )
    args = parser.parse_args()

    record = get_registry_record(args.product_id)
    docs_root, _ = client_paths(args.product_id)
    client_cfg = dict(record.get("client") or {})
    billing_status = str(client_cfg.get("billing_status", ""))
    if args.metrics_json:
        metrics = load_monthly_metrics(args.metrics_json)
    elif args.site_id:
        client = default_stats_client()
        if client is None:
            print("ERROR: PLAUSIBLE_API_KEY not set", file=sys.stderr)
            return 1
        # A missing 'Form Lead' goal no longer fails the report: traffic is still
        # reported and leads are flagged "Not tracked yet" (never a fake 0).
        metrics = metrics_from_plausible(
            client,
            product_id=args.product_id,
            month=args.month,
            site_id=args.site_id,
            completed_work=args.completed_work,
            recommended_action=args.recommended_action,
            billing_status=billing_status,
            bookings=args.bookings,
        )
    else:
        metrics = MonthlyMetrics(
            product_id=args.product_id,
            month=args.month,
            visits=args.visits,
            form_leads=args.form_leads,
            bookings=args.bookings,
            completed_work=args.completed_work,
            recommended_action=args.recommended_action,
            billing_status=billing_status,
        )
    client_name = str(record.get("name", args.product_id))
    path = write_monthly_report(docs_root, metrics, client_name=client_name)
    print(json.dumps({"report": str(path.relative_to(REPO))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
