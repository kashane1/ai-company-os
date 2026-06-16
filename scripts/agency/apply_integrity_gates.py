#!/usr/bin/env python3
"""Apply BBW integrity gates across the prospect database.

Currently runs one gate: the **non-attorney immigration-paperwork** category
gate (notario-fraud zone). See ``packages/prospecting/integrity_gates.py`` for
the policy and its coverage limit (name/types only — not review text).

Default is a dry run: it lists every prospect the gate would suppress so an
operator can review the candidate list. Pass ``--apply`` to hard-exclude the
matches by writing them to the fail-closed suppression registry
(``source=disqualified``). Suppression is one-way in code; reversing a specific
false positive is a deliberate founder edit of the registry.

    # review the candidates (no writes)
    python3 scripts/agency/apply_integrity_gates.py

    # hard-exclude them
    python3 scripts/agency/apply_integrity_gates.py --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.outreach_store import OutreachStore  # noqa: E402
from packages.agency.suppression import is_suppressed, suppress  # noqa: E402
from packages.prospecting.integrity_gates import (  # noqa: E402
    evaluate_record_for_exclusion,
)

RECORDS_DIR = REPO / "state" / "prospects" / "records"


def _iter_records():
    for path in sorted(RECORDS_DIR.glob("*.json")):
        try:
            yield json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="hard-exclude matches (write to the suppression registry). Default: dry run.",
    )
    parser.add_argument("--json", action="store_true", help="print matches as JSON")
    args = parser.parse_args()

    store = OutreachStore()
    matches: list[dict[str, object]] = []
    for record in _iter_records():
        result = evaluate_record_for_exclusion(record)
        if not result.matched:
            continue
        matches.append(
            {
                "place_id": record.get("place_id"),
                "display_name": record.get("display_name"),
                "genre_id": record.get("genre_id"),
                "rating": record.get("rating"),
                "reviews": record.get("user_ratings_total"),
                "terms": result.terms,
                "already_suppressed": is_suppressed(record, store=store),
                "reason": result.reason(),
            }
        )

    if args.json:
        print(json.dumps(matches, indent=2))
    else:
        verb = "Suppressing" if args.apply else "Would suppress"
        print(f"{verb} {len(matches)} immigration-paperwork prospect(s):\n")
        for m in matches:
            flag = " [already suppressed]" if m["already_suppressed"] else ""
            print(
                f"  {m['display_name']!r}  {m['place_id']}  "
                f"{m['genre_id']} {m['rating']}/{m['reviews']}  "
                f"matched={m['terms']}{flag}"
            )

    if not args.apply:
        print("\nDry run — no changes. Re-run with --apply to hard-exclude.")
        return

    written = 0
    for record in _iter_records():
        result = evaluate_record_for_exclusion(record)
        if not result.matched or is_suppressed(record, store=store):
            continue
        suppress(record, reason=result.reason(), source="disqualified", store=store)
        written += 1
    print(f"\nApplied: suppressed {written} newly-matched prospect(s).")


if __name__ == "__main__":
    main()
