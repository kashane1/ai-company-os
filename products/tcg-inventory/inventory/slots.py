"""Binder slot allocation.

A slot is a permanent address. Cards move; slot numbers never do. Page and
pocket are derived rather than stored, so re-sleeving into different pages is a
config change instead of a migration.

Slots are reused. When a card is pulled against an order its slot returns to
the free list and the next card listed drops into it, which keeps the binder
dense and bounded rather than growing holes forever. Allocation always takes
the lowest free slot, so the binder fills front to back and the gaps you can
see are real unsold capacity.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


class BinderFull(RuntimeError):
    """Every slot in the binder is occupied."""


@dataclass(frozen=True)
class SlotAddress:
    slot_number: int
    binder_name: str
    page: int
    pocket: int

    def __str__(self) -> str:
        return f"{self.binder_name}, Page {self.page}, Pocket {self.pocket}"


def address(conn: sqlite3.Connection, slot_number: int) -> SlotAddress:
    """Turn a slot number into something you can physically find."""
    binder = conn.execute(
        """
        SELECT * FROM binders
         WHERE ? BETWEEN first_slot AND last_slot
         LIMIT 1
        """,
        (slot_number,),
    ).fetchone()
    if binder is None:
        raise KeyError(f"Slot {slot_number} is not in any configured binder")

    per_page = binder["pockets_per_page"]
    offset = slot_number - binder["first_slot"]
    return SlotAddress(
        slot_number=slot_number,
        binder_name=binder["binder_name"],
        page=offset // per_page + 1,
        pocket=offset % per_page + 1,
    )


def occupied_slots(conn: sqlite3.Connection) -> dict[int, int]:
    """slot_number -> copy_id, for every slot currently holding a card."""
    return {
        row["slot_number"]: row["copy_id"]
        for row in conn.execute("SELECT slot_number, copy_id FROM slot_occupancy")
    }


def next_free_slot(conn: sqlite3.Connection, binder_name: str | None = None) -> int:
    """The lowest unoccupied slot. Raises BinderFull when there is none."""
    binders = conn.execute(
        "SELECT * FROM binders WHERE (? IS NULL OR binder_name = ?) ORDER BY first_slot",
        (binder_name, binder_name),
    ).fetchall()
    if not binders:
        raise KeyError(f"No binder configured: {binder_name}")

    taken = occupied_slots(conn)
    for binder in binders:
        for slot in range(binder["first_slot"], binder["last_slot"] + 1):
            if slot not in taken:
                return slot

    raise BinderFull(
        "Every slot is occupied. Pull something, or add a binder row with a "
        "higher slot range."
    )


def find_copy(conn: sqlite3.Connection, copy_id: int) -> SlotAddress | None:
    """Where a copy physically is, or None if it isn't in a binder."""
    row = conn.execute(
        "SELECT slot_number FROM slot_occupancy WHERE copy_id = ?", (copy_id,)
    ).fetchone()
    return address(conn, row["slot_number"]) if row else None


def capacity(conn: sqlite3.Connection) -> dict[str, int]:
    taken = len(occupied_slots(conn))
    total = conn.execute(
        "SELECT COALESCE(SUM(last_slot - first_slot + 1), 0) AS n FROM binders"
    ).fetchone()["n"]
    return {"total": total, "occupied": taken, "free": total - taken}
