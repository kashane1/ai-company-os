#!/usr/bin/env python3
"""Plan a monthly retainer run for a client site."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.registry import get_registry_record  # noqa: E402
from packages.agency.retainer_ops import plan_retainer_run, write_retainer_run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--month", required=True, help="YYYY-MM")
    parser.add_argument("--state-root", type=Path, default=REPO / "state")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    record = get_registry_record(args.product_id)
    run = plan_retainer_run(record, month=args.month)
    payload = run.to_dict()
    if not args.dry_run:
        payload["path"] = str(write_retainer_run(args.state_root, run).relative_to(REPO))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
