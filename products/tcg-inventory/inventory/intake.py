"""Bringing cards into inventory, and putting them on a marketplace.

Every function here writes the domain row and its ledger event together in one
transaction. That pairing is the invariant the whole system rests on: a
listings row with no corresponding event, or a slot assignment the log does not
know about, is drift that reconciliation cannot explain later.

Cost basis is the part worth reading closely. You almost never buy one card at
a known price — you buy a collection for $400 and it has 600 cards in it. The
allocation here is pro-rata by market value at acquisition, which is the method
that makes per-card profit mean anything afterward.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from . import catalog, ledger, slots


class NoCatalogEntry(KeyError):
    """The variant does not exist in the attached catalog."""


class AlreadyListed(RuntimeError):
    """This copy is already live on that channel."""


@dataclass(frozen=True)
class IntakeResult:
    copy_id: int
    variant_id: int
    card_name: str
    set_name: str
    sub_type: str
    condition_code: str
    market_price_cents: int | None
    slot: slots.SlotAddress | None


# ─── Acquisitions ────────────────────────────────────────────────────────────

def create_acquisition(
    conn: sqlite3.Connection,
    acquired_on: str,
    total_cost_cents: int,
    *,
    source: str | None = None,
    note: str | None = None,
) -> int:
    """Record a lot you bought. Cards are attached to it as they're catalogued."""
    cursor = conn.execute(
        """
        INSERT INTO acquisitions (acquired_on, source, total_cost_cents, note)
        VALUES (?, ?, ?, ?)
        """,
        (acquired_on, source, total_cost_cents, note),
    )
    conn.commit()
    return cursor.lastrowid


def allocate_lot_cost(conn: sqlite3.Connection, acquisition_id: int) -> dict[int, int]:
    """Spread a lot's cost across its copies, pro-rata by market value.

    Returns copy_id -> allocated cents.

    Two details that matter more than they look:

    Allocations are forced to sum to the lot total exactly, using largest
    remainder. Rounding each share independently loses or invents cents, and
    since cost basis feeds both pricing floors and taxes, it needs to tie out.

    Copies the catalog cannot price fall back to an equal share of whatever is
    left rather than being assigned zero. A zero basis would make a card look
    infinitely profitable and would quietly corrupt every margin report that
    includes it.
    """
    lot = conn.execute(
        "SELECT * FROM acquisitions WHERE acquisition_id = ?", (acquisition_id,)
    ).fetchone()
    if lot is None:
        raise KeyError(f"No acquisition {acquisition_id}")

    copies = conn.execute(
        "SELECT copy_id, variant_id, condition_code FROM copies WHERE acquisition_id = ?",
        (acquisition_id,),
    ).fetchall()
    if not copies:
        return {}

    total = lot["total_cost_cents"]
    weights: dict[int, int] = {}
    for row in copies:
        price = catalog.market_price_cents(conn, row["variant_id"], row["condition_code"])
        weights[row["copy_id"]] = price or 0

    weight_sum = sum(weights.values())
    if weight_sum == 0:
        # Nothing is priceable; split evenly.
        weights = {copy_id: 1 for copy_id in weights}
        weight_sum = len(weights)

    exact = {cid: total * w / weight_sum for cid, w in weights.items()}
    allocated = {cid: int(value) for cid, value in exact.items()}

    # Largest remainder: hand out the leftover cents to the biggest fractions.
    shortfall = total - sum(allocated.values())
    by_remainder = sorted(exact, key=lambda cid: exact[cid] - allocated[cid], reverse=True)
    for cid in by_remainder[:shortfall]:
        allocated[cid] += 1

    conn.executemany(
        "UPDATE copies SET cost_cents = ? WHERE copy_id = ?",
        [(cents, cid) for cid, cents in allocated.items()],
    )
    conn.commit()
    return allocated


# ─── Intake ──────────────────────────────────────────────────────────────────

def add_copy(
    conn: sqlite3.Connection,
    variant_id: int,
    condition_code: str = "NM",
    *,
    acquisition_id: int | None = None,
    cost_cents: int | None = None,
    note: str | None = None,
    acquired_on: str | None = None,
    assign_slot: bool = True,
) -> IntakeResult:
    """Catalogue one physical card and, by default, put it in the binder.

    `assign_slot=False` is for cards going into the keeper collection — they
    are still tracked and still carry a cost basis, they just do not consume
    binder capacity.
    """
    card = catalog.get_variant(conn, variant_id)
    if card is None:
        raise NoCatalogEntry(f"No catalog variant {variant_id}")

    cursor = conn.execute(
        """
        INSERT INTO copies (variant_id, product_id, condition_code, acquisition_id, cost_cents, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            variant_id,
            card["product_id"],
            condition_code,
            acquisition_id,
            cost_cents,
            note,
        ),
    )
    copy_id = cursor.lastrowid

    ledger.record(
        conn,
        copy_id,
        "acquired",
        occurred_at=acquired_on,
        price_cents=cost_cents,
        detail={"acquisition_id": acquisition_id} if acquisition_id else None,
    )

    slot_address = slot_copy(conn, copy_id) if assign_slot else None

    return IntakeResult(
        copy_id=copy_id,
        variant_id=variant_id,
        card_name=card["card_name"],
        set_name=card["set_name"],
        sub_type=card["sub_type"],
        condition_code=condition_code,
        market_price_cents=catalog.market_price_cents(conn, variant_id, condition_code),
        slot=slot_address,
    )


def slot_copy(
    conn: sqlite3.Connection, copy_id: int, slot_number: int | None = None
) -> slots.SlotAddress:
    """Put a copy in the binder. Takes the lowest free slot unless told otherwise."""
    if slot_number is None:
        slot_number = slots.next_free_slot(conn)
    else:
        occupant = slots.occupied_slots(conn).get(slot_number)
        if occupant is not None and occupant != copy_id:
            raise ValueError(f"Slot {slot_number} already holds copy {occupant}")

    ledger.record(conn, copy_id, "slotted", slot_number=slot_number)
    return slots.address(conn, slot_number)


def pull_copy(conn: sqlite3.Connection, copy_id: int) -> slots.SlotAddress | None:
    """Physically remove a copy from its slot, freeing it for reuse."""
    address = slots.find_copy(conn, copy_id)
    if address is None:
        return None
    ledger.record(conn, copy_id, "pulled", slot_number=address.slot_number)
    return address


# ─── Listing ─────────────────────────────────────────────────────────────────

def list_copy(
    conn: sqlite3.Connection,
    copy_id: int,
    channel: str,
    list_price_cents: int,
    *,
    external_ref: str | None = None,
    listing_title: str | None = None,
    listed_at: str | None = None,
) -> int:
    """Open a listing for a copy on a channel. Returns the listing id.

    `listing_title` is what the card is called on the marketplace. It is worth
    recording even though nothing needs it to list: eBay's sale notification
    carries no item number, so the title is the only handle a sale email has on
    the copy that sold.
    """
    live = conn.execute(
        """
        SELECT listing_id FROM listings
         WHERE copy_id = ? AND channel = ? AND ended_at IS NULL
        """,
        (copy_id, channel),
    ).fetchone()
    if live is not None:
        raise AlreadyListed(f"Copy {copy_id} is already live on {channel}")

    listed_at = listed_at or conn.execute("SELECT datetime('now') AS t").fetchone()["t"]
    cursor = conn.execute(
        """
        INSERT INTO listings
            (copy_id, channel, external_ref, listing_title, list_price_cents, listed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (copy_id, channel, external_ref, listing_title, list_price_cents, listed_at),
    )
    ledger.record(
        conn,
        copy_id,
        "listed",
        channel=channel,
        price_cents=list_price_cents,
        external_ref=external_ref,
        occurred_at=listed_at,
    )
    return cursor.lastrowid


def end_listing(
    conn: sqlite3.Connection,
    listing_id: int,
    reason: str,
    *,
    ended_at: str | None = None,
    idempotency_key: str | None = None,
) -> None:
    """Close a listing. `reason` is sold | delisted | expired | oversold.

    A sale closes the listing but does NOT move the card: it is still sitting
    in its binder slot until someone physically pulls it. `idempotency_key`
    should always be supplied when this is driven by a marketplace
    notification, since those get delivered twice.
    """
    row = conn.execute(
        "SELECT * FROM listings WHERE listing_id = ?", (listing_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"No listing {listing_id}")
    if row["ended_at"] is not None:
        return
    if idempotency_key is not None and ledger.has_key(conn, idempotency_key):
        return

    # The UPDATE goes first and `record` commits both together, so a crash
    # between them cannot leave the event written and the listing still open.
    ended_at = ended_at or conn.execute("SELECT datetime('now') AS t").fetchone()["t"]
    conn.execute(
        "UPDATE listings SET ended_at = ?, end_reason = ? WHERE listing_id = ?",
        (ended_at, reason, listing_id),
    )
    ledger.record(
        conn,
        row["copy_id"],
        "sold" if reason == "sold" else "delisted",
        channel=row["channel"],
        price_cents=row["list_price_cents"],
        external_ref=row["external_ref"],
        occurred_at=ended_at,
        idempotency_key=idempotency_key,
    )


def live_listings(conn: sqlite3.Connection, copy_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM listings WHERE copy_id = ? AND ended_at IS NULL", (copy_id,)
    ).fetchall()
