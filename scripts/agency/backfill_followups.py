#!/usr/bin/env python3
"""Backfill ``next_touch_at`` for sent rows that never got a follow-up scheduled.

Fix item F2: the first real sends (logged 2026-06-12) carry ``status="sent"`` and
a correct ``last_touch_at`` but ``next_touch_at=""`` — they predate the sequencer
commits, so the due-queue stayed empty and those prospects would silently never
get touch 2. This one-shot, idempotent backfill computes the per-step cadence for
every such row from its real outbound touch count and anchors it at the row's
``last_touch_at`` (so the schedule matches when the send actually happened).

    python scripts/agency/backfill_followups.py            # dry-run (default)
    python scripts/agency/backfill_followups.py --apply     # write the ledger

Idempotent: a row that already has ``next_touch_at`` (or whose sequence is
complete) is left untouched, so re-running changes nothing. Suppressed and
terminal-status rows are skipped — they have no pending follow-up by design.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency import suppression  # noqa: E402
from packages.agency.outreach_lane import (  # noqa: E402
    TERMINAL_STATUSES,
    OutreachClientRow,
    OutreachLaneStatus,
    _mutate_row,
    default_outreach_lane_root,
    load_existing_rows,
)
from packages.agency.outreach_sequencer import schedule_next_touch  # noqa: E402
from packages.agency.outreach_store import OutreachStore  # noqa: E402

# Rows in a post-send, non-terminal state are the ones a follow-up cadence applies
# to. Pre-send (needs_bespoke/ready_*) and blocked rows haven't been sent; terminal
# rows (replied/won/lost/DNC) have no pending automated follow-up.
SENT_CLASS_STATUSES = {OutreachLaneStatus.SENT, OutreachLaneStatus.FOLLOW_UP_DUE}


def _candidates(lane_root: Path, store: OutreachStore) -> list[tuple[OutreachClientRow, str]]:
    """Rows needing a backfilled ``next_touch_at`` and the value to write."""
    rows = [OutreachClientRow.from_dict(r) for r in load_existing_rows(lane_root).values()]
    touch_summary = store.touch_summary()
    suppressed = store.suppressed_keys()
    out: list[tuple[OutreachClientRow, str]] = []
    for row in rows:
        if row.status in TERMINAL_STATUSES or row.status not in SENT_CLASS_STATUSES:
            continue
        if row.next_touch_at:  # already scheduled — idempotent skip
            continue
        if not row.last_touch_at:  # no anchor to schedule from
            continue
        if suppressed and any(
            key in suppressed
            for _kind, key in suppression.keys_for_record(_row_record(row))
        ):
            continue
        outbound_count = sum(
            int(s.get("count", 0) or 0)
            for s in touch_summary.get(row.place_id, {}).values()
        )
        if outbound_count <= 0:  # no real send recorded — nothing to follow up
            continue
        next_touch = schedule_next_touch(outbound_count, row.last_touch_at)
        if not next_touch:  # sequence already complete (>= MAX_TOUCHES)
            continue
        out.append((row, next_touch))
    return out


def _row_record(row: OutreachClientRow) -> dict[str, object]:
    return {
        "place_id": row.place_id,
        "contact_email": row.contact_email,
        "phone": row.phone,
        "contact_instagram": row.contact_instagram,
        "contact_facebook": row.contact_facebook,
    }


def run_backfill(
    *, lane_root: Path, store: OutreachStore, apply: bool
) -> list[tuple[OutreachClientRow, str]]:
    """Find (and, when ``apply``, write) the rows needing a ``next_touch_at``.

    Returns the candidate ``(row, next_touch_at)`` pairs. Idempotent: once applied,
    rows have a ``next_touch_at`` so a re-run returns an empty list.
    """
    candidates = _candidates(lane_root, store)
    if apply:
        for row, next_touch in candidates:
            _mutate_row(
                row.place_id,
                lambda _r, nt=next_touch: {"next_touch_at": nt},
                lane_root=lane_root,
            )
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="write the ledger (default: dry-run)")
    args = parser.parse_args()

    lane_root = default_outreach_lane_root()
    store = OutreachStore()
    candidates = run_backfill(lane_root=lane_root, store=store, apply=args.apply)

    if not candidates:
        print("no rows need a follow-up backfill — ledger is already consistent.")
        return 0

    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(candidates)} row(s) need next_touch_at:")
    for row, next_touch in candidates:
        print(f"  {row.business_name:<34} sent {row.last_touch_at}  ->  next_touch {next_touch}")

    if not args.apply:
        print("\n(dry-run) re-run with --apply to write these.")
    else:
        print(f"\napplied {len(candidates)} backfill(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
