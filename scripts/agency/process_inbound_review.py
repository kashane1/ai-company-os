#!/usr/bin/env python3
"""Audit + (optionally) build a preview for one captured inbound lead (G2b).

Examples:
  # audit the submitted website only (no city/genre → no preview yet):
  python scripts/agency/process_inbound_review.py --id <submission_id>

  # also build a local preview (operator supplies the form's missing inputs):
  python scripts/agency/process_inbound_review.py --id <id> --city "Austin, TX" --genre plumber

  # re-run an already-processed lead:
  python scripts/agency/process_inbound_review.py --id <id> --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.inbound_fulfillment import process_inbound_review  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--id", dest="submission_id", required=True)
    parser.add_argument("--city", default="", help="city for the preview build (form omits it)")
    parser.add_argument("--genre", default="", help="business genre, e.g. plumber / barber_shop")
    parser.add_argument("--force", action="store_true", help="re-run an already-processed lead")
    parser.add_argument("--inbound-root", type=Path, default=None)
    args = parser.parse_args()

    try:
        result = process_inbound_review(
            args.submission_id,
            city=args.city,
            genre=args.genre,
            force=args.force,
            inbound_root=args.inbound_root,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
