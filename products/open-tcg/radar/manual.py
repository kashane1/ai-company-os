"""Founder-entered observations: Guppy alerts (the benchmark) and sightings."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
from typing import Iterable

from . import matching
from .db import iso
from .social import parse
from .watchlist import WatchItem

KINDS = ("guppy", "sighting")


def log(
    connection: sqlite3.Connection,
    *,
    kind: str,
    text: str,
    at: dt.datetime,
    watch: Iterable[WatchItem],
    set_keys: Iterable[str],
    now: dt.datetime,
    retailer: str | None = None,
) -> int:
    """Store one manual entry; returns its observation id."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    keys = list(set_keys)
    post = parse.parse_post({"text": text}, set_keys=keys)
    # A Guppy alert or a sighting means the item was available.
    signal = post.signal if post.signal in {"preorder", "queue", "drop", "invites", "drawing_open"} else "in_stock"
    external_id = f"{kind}:{iso(at)}:{hashlib.sha1(text.encode()).hexdigest()[:10]}"
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO observations
            (source_id, external_id, author, text, signal, retailer, product_text, price, url,
             is_tcg, watch_matches, source_time, received_at)
        VALUES (?, ?, 'founder', ?, ?, ?, ?, ?, NULL, 1, ?, ?, ?)
        """,
        (
            kind, external_id, text, signal, retailer or post.retailer, post.product_text, post.price,
            json.dumps(matching.watch_matches(text, watch, keys)), iso(at), iso(now),
        ),
    )
    connection.commit()
    if cursor.rowcount:
        return cursor.lastrowid
    return connection.execute(
        "SELECT id FROM observations WHERE source_id = ? AND external_id = ?", (kind, external_id)
    ).fetchone()["id"]
