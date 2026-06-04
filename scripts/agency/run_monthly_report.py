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
    write_monthly_report,
)
from packages.agency.plausible import (  # noqa: E402
    GoalNotConfigured,
    default_stats_client,
    fetch_monthly_stats,
    month_to_date_range,
)
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
    args = parser.parse_args()

    record = get_registry_record(args.product_id)
    docs_root, _ = client_paths(args.product_id)
    if args.metrics_json:
        metrics = load_monthly_metrics(args.metrics_json)
    else:
        visits, form_leads = args.visits, args.form_leads
        if args.site_id:
            client = default_stats_client()
            if client is None:
                print("ERROR: PLAUSIBLE_API_KEY not set", file=sys.stderr)
                return 1
            try:
                stats = fetch_monthly_stats(
                    client, site_id=args.site_id, date_range=month_to_date_range(args.month)
                )
            except GoalNotConfigured as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 2
            visits, form_leads = stats.visits, stats.form_leads
        client_cfg = dict(record.get("client") or {})
        metrics = MonthlyMetrics(
            product_id=args.product_id,
            month=args.month,
            visits=visits,
            form_leads=form_leads,
            completed_work=args.completed_work,
            recommended_action=args.recommended_action,
            billing_status=str(client_cfg.get("billing_status", "")),
        )
    client_name = str(record.get("name", args.product_id))
    path = write_monthly_report(docs_root, metrics, client_name=client_name)
    print(json.dumps({"report": str(path.relative_to(REPO))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
