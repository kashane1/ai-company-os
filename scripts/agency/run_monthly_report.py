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
from packages.agency.monthly_report import MonthlyMetrics, load_monthly_metrics, write_monthly_report  # noqa: E402
from packages.agency.registry import get_registry_record  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--month", required=True, help="YYYY-MM")
    parser.add_argument("--metrics-json", type=Path)
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
        client = dict(record.get("client") or {})
        metrics = MonthlyMetrics(
            product_id=args.product_id,
            month=args.month,
            visits=args.visits,
            form_leads=args.form_leads,
            completed_work=args.completed_work,
            recommended_action=args.recommended_action,
            billing_status=str(client.get("billing_status", "")),
        )
    path = write_monthly_report(docs_root, metrics, client_name=str(record.get("name", args.product_id)))
    print(json.dumps({"report": str(path.relative_to(REPO))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
