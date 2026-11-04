"""Build a demo inventory at realistic scale, for exercising the selector.

Writes to data/demo.db — never to data/inventory.db — so a real collection is
never touched by this. Draws real cards from the attached catalog matching the
stated distribution: ~400 sellable cards under $10 and ~100 between $10 and $50,
"ex or better", nothing above $50.

    python scripts/make_demo_inventory.py [--copies 500]
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inventory import db, intake  # noqa: E402

DEMO_DB = db.PROJECT_ROOT / "data" / "demo.db"

# Roughly his stated mix. Condition skews to NM for modern singles.
CHEAP_SHARE = 0.8
CONDITIONS = (["NM"] * 7) + (["LP"] * 2) + ["MP"]


def pick_variants(conn, low: float, high: float, count: int) -> list[int]:
    """Real catalog variants in a price band, biased toward playable rarities."""
    rows = conn.execute(
        """
        SELECT variant_id
          FROM catalog.screener_rows
         WHERE current_price BETWEEN ? AND ?
           AND rarity IS NOT NULL
           AND rarity NOT IN ('Common', 'Uncommon')
           AND card_name NOT LIKE '%Code Card%'
         ORDER BY RANDOM()
         LIMIT ?
        """,
        (low, high, count),
    ).fetchall()
    return [row["variant_id"] for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--copies", type=int, default=500)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    random.seed(args.seed)
    DEMO_DB.unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        Path(str(DEMO_DB) + suffix).unlink(missing_ok=True)

    conn = db.connect(DEMO_DB)
    db.initialize(conn)

    # A binder big enough that the binder, not the channel cap, is never what
    # limits the plan — the point is to exercise the channel caps.
    conn.execute("UPDATE binders SET last_slot = ? WHERE binder_name = 'Binder 1'",
                 (args.copies + 50,))
    conn.commit()

    cheap_count = int(args.copies * CHEAP_SHARE)
    variants = (
        pick_variants(conn, 0.50, 9.99, cheap_count)
        + pick_variants(conn, 10.00, 50.00, args.copies - cheap_count)
    )
    if not variants:
        print("No catalog rows matched — is the catalog built?", file=sys.stderr)
        return 1

    lot = intake.create_acquisition(
        conn, "2026-10-01", 40000, source="demo collection buy"
    )
    for variant_id in variants:
        intake.add_copy(
            conn, variant_id, random.choice(CONDITIONS), acquisition_id=lot
        )

    intake.allocate_lot_cost(conn, lot)

    total = conn.execute("SELECT COUNT(*) AS n FROM copies").fetchone()["n"]
    print(f"Wrote {total} copies to {DEMO_DB}")
    print("Inspect with:")
    print(f"  INVENTORY_DB={DEMO_DB} python -m inventory plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
