#!/usr/bin/env python3
"""Apply verified Stripe billing events to the local agency ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.billing import (  # noqa: E402
    BillingReconciliationError,
    reconcile_stripe_event_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--events-dir",
        type=Path,
        default=REPO / "state" / "agency" / "stripe-events",
        help="directory of verified Stripe event JSON files from the Netlify receiver",
    )
    parser.add_argument(
        "--billing-root",
        type=Path,
        default=REPO / "state" / "agency" / "billing",
    )
    parser.add_argument("--registry-path", type=Path, default=REPO / "infra" / "products.json")
    args = parser.parse_args()

    if not args.events_dir.exists():
        print(json.dumps({"processed": 0, "events_dir": str(args.events_dir)}, indent=2))
        return 0

    # Order-independent drain (multi-pass / defer-on-miss). A metadata-less
    # invoice.paid can only reconcile AFTER checkout.session.completed seeds the
    # ledger, but Stripe gives no ordering guarantee and event-id filenames sort
    # randomly. So we retry deferred events across passes until a pass makes no
    # progress; only then are the stragglers real errors. Without this, ~half of
    # real sales (invoice.paid sorted before its seed event) would abort the drain.
    processed: list[dict] = []
    pending = sorted(args.events_dir.glob("*.json"))
    while pending:
        deferred: list[Path] = []
        progressed = False
        for path in pending:
            try:
                ledger = reconcile_stripe_event_file(
                    path, billing_root=args.billing_root, registry_path=args.registry_path
                )
            except BillingReconciliationError:
                deferred.append(path)  # likely waiting on a seed event this batch
                continue
            processed.append(
                {"event": path.name, "product_id": ledger.product_id, "status": ledger.billing_status}
            )
            progressed = True
        if not progressed:
            # No event reconciled this pass — the deferred ones are genuine errors.
            for path in deferred:
                try:
                    reconcile_stripe_event_file(
                        path, billing_root=args.billing_root, registry_path=args.registry_path
                    )
                except BillingReconciliationError as exc:
                    print(f"ERROR {path.name}: {exc}", file=sys.stderr)
            print(json.dumps({"processed": processed, "errored": [p.name for p in deferred]}, indent=2))
            return 2
        pending = deferred
    print(json.dumps({"processed": processed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
