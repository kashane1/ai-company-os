#!/usr/bin/env python3
"""Promote one pulled self-serve order into a client-site registry record.

Run AFTER scripts/web/pull-orders.mjs and BEFORE the stripe-events drain, so the
registry record exists when invoice.paid reconciles (else it dead-letters).

Examples:
  python scripts/agency/process_inbound_order.py --id joes-plumbing-ab12cd34
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.order_fulfillment import process_inbound_order  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--id", dest="product_id", required=True)
    parser.add_argument("--inbound-root", type=Path, default=None)
    args = parser.parse_args()

    try:
        record = process_inbound_order(args.product_id, inbound_root=args.inbound_root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
