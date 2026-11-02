"""The append-only event log, and the state it projects.

Nothing here updates or deletes. A mistake is corrected by appending the
correcting event, so the question "why is this card in the outbound tray?" is
always answerable six weeks later.

The important guarantee is idempotency. Order notifications arrive as eBay
webhooks and TCGplayer emails, and both will be delivered twice eventually. A
replayed notification carrying the same idempotency key is a no-op at the
database level rather than a phantom second sale that decrements stock still
sitting in the binder.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class RecordedEvent:
    event_id: int
    was_duplicate: bool


def record(
    conn: sqlite3.Connection,
    copy_id: int,
    kind: str,
    *,
    occurred_at: str | None = None,
    channel: str | None = None,
    slot_number: int | None = None,
    price_cents: int | None = None,
    external_ref: str | None = None,
    detail: dict | None = None,
    idempotency_key: str | None = None,
) -> RecordedEvent:
    """Append one event. Returns the existing event if the key was already used.

    Callers that process an external notification should always pass an
    idempotency_key built from the marketplace's own identifiers — for example
    `ebay:order:12-34567-89012:item:445`. Without one, a retried webhook writes
    a second sale.
    """
    if idempotency_key is not None:
        existing = conn.execute(
            "SELECT event_id FROM events WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            return RecordedEvent(event_id=existing["event_id"], was_duplicate=True)

    cursor = conn.execute(
        """
        INSERT INTO events (
            copy_id, kind, occurred_at, channel, slot_number,
            price_cents, external_ref, detail, idempotency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            copy_id,
            kind,
            occurred_at or _now(),
            channel,
            slot_number,
            price_cents,
            external_ref,
            json.dumps(detail) if detail is not None else None,
            idempotency_key,
        ),
    )
    conn.commit()
    return RecordedEvent(event_id=cursor.lastrowid, was_duplicate=False)


def has_key(conn: sqlite3.Connection, idempotency_key: str) -> bool:
    """Whether this notification has already been processed.

    Callers that must write more than the event itself check this up front and
    bail, rather than relying on `record` reporting a duplicate afterwards —
    by then their own writes have already happened.
    """
    row = conn.execute(
        "SELECT 1 FROM events WHERE idempotency_key = ?", (idempotency_key,)
    ).fetchone()
    return row is not None


def current_state(conn: sqlite3.Connection, copy_id: int) -> str | None:
    row = conn.execute(
        "SELECT state FROM copy_current_state WHERE copy_id = ?", (copy_id,)
    ).fetchone()
    return row["state"] if row else None


def history(conn: sqlite3.Connection, copy_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT e.*, k.resulting_state
          FROM events e
          JOIN event_kinds k ON k.kind = e.kind
         WHERE e.copy_id = ?
         ORDER BY e.occurred_at, e.event_id
        """,
        (copy_id,),
    ).fetchall()


def copies_in_state(conn: sqlite3.Connection, state: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM copy_current_state WHERE state = ? ORDER BY copy_id", (state,)
    ).fetchall()


def reconcile_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """How many copies sit in each state. The number to eyeball against reality.

    Run it against the physical containers: if the ledger says nine cards are
    in the outbound tray and the tray holds eight, something upstream is wrong
    and it is better to find out now than at the next oversell.
    """
    rows = conn.execute(
        """
        SELECT COALESCE(state, 'unknown') AS state, COUNT(*) AS copy_count
          FROM copy_current_state
         GROUP BY state
        """
    ).fetchall()
    return {r["state"]: r["copy_count"] for r in rows}
