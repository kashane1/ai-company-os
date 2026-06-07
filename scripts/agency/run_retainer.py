#!/usr/bin/env python3
"""Plan a monthly retainer run for a client site."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.registry import get_registry_record  # noqa: E402
from packages.agency.retainer_executor import (  # noqa: E402
    default_safe_executors,
    execute_retainer_run,
)
from packages.agency.retainer_ops import plan_retainer_run, write_retainer_run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--month", required=True, help="YYYY-MM")
    parser.add_argument("--state-root", type=Path, default=REPO / "state")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="run the safe prep actions (drafts/health checks); outward steps stay gated",
    )
    parser.add_argument(
        "--as-of", default="", help="reference date YYYY-MM-DD for --execute (default: today)"
    )
    args = parser.parse_args()

    record = get_registry_record(args.product_id)
    run = plan_retainer_run(record, month=args.month)
    payload = run.to_dict()
    if not args.dry_run:
        payload["path"] = str(write_retainer_run(args.state_root, run).relative_to(REPO))

    if args.execute:
        as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc).date()
        report = execute_retainer_run(
            run,
            executors=default_safe_executors(state_root=args.state_root, as_of=as_of),
            state_root=args.state_root,
            mark_complete=not args.dry_run,
        )
        payload["execution"] = report.to_dict()
        print(json.dumps(payload, indent=2))
        return 0 if report.ok() else 1

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
