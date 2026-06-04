#!/usr/bin/env python3
"""Operator CLI — promote a human-verified prospect into a client engagement.

Promotion is approval-gated: it requires ``--approved-by NAME`` (a recorded
operator approval) and the prospect must already be human-verified. Promotion
does not send outreach; it writes a ``client-site`` record into the product
registry and scaffolds the client docs workspace.

Examples::

    python3 scripts/promote_prospect.py list-verified
    python3 scripts/promote_prospect.py promote --place-id PLACE --bundle package_a \\
        --approved-by kashane
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.agency.catalog import default_catalog  # noqa: E402
from packages.agency.promotion import PromotionError, promote_prospect_to_client  # noqa: E402
from packages.policies.approvals import PolicyViolation  # noqa: E402
from packages.prospecting.storage import ProspectRepository  # noqa: E402
from packages.schemas.prospect import HumanVerified  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote a verified prospect to a client")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-verified", help="list human-verified prospects eligible for promotion")

    promote = sub.add_parser("promote", help="promote one prospect into a client-site record")
    promote.add_argument("--place-id", required=True)
    promote.add_argument("--bundle", required=True, choices=sorted(default_catalog().bundles))
    promote.add_argument(
        "--approved-by",
        required=True,
        help="operator name recording the founder approval for this promotion",
    )

    args = parser.parse_args(argv)
    repo = ProspectRepository()

    if args.command == "list-verified":
        verified = [r for r in repo.list() if r.human_verified is HumanVerified.TRUE]
        if not verified:
            print("No human-verified prospects found.")
            return 0
        for record in verified:
            print(f"{record.place_id}\t{record.display_name}\t{record.formatted_address}")
        return 0

    # promote
    record = repo.get(args.place_id)
    try:
        result = promote_prospect_to_client(
            record,
            args.bundle,
            approval_granted=bool(args.approved_by),
        )
    except PolicyViolation as exc:
        print(f"REFUSED [{exc.code}]: {exc}", file=sys.stderr)
        return 2
    except PromotionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Promoted {record.display_name} -> {result['id']} (bundle {args.bundle})")
    print(f"  docs:  docs/products/{result['id']}/")
    print(f"  code:  products/{result['id']}/  (run client_intake to scaffold)")
    print("  next:")
    print(f"    python scripts/agency/client_intake.py --product-id {result['id']} "
          f"--from-prospect {args.place_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
