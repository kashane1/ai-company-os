"""Notifications for watched restocks. One per episode, only while it is fresh.

The channel is a native macOS notification (phone push via ntfy is paused).
A notification fires when an episode is for a watched item, is an
availability signal (in stock, pre-order, drop, queue, invites, open
drawing), opened within MAX_AGE, and has no known price above the item's
alert threshold.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import subprocess
from typing import Callable, Iterable

from . import watchlist
from .db import iso
from .watchlist import WatchItem

MAX_AGE = dt.timedelta(minutes=15)
SIGNAL_LABELS = {
    "in_stock": "In stock",
    "preorder": "Pre-order open",
    "drop": "Drop",
    "queue": "Queue open",
    "invites": "Invites going out",
    "drawing_open": "Drawing open",
}

Sender = Callable[[str, str], None]


def macos_notify(title: str, body: str) -> None:
    # Title and body are passed as arguments, never interpolated into AppleScript.
    subprocess.run(
        [
            "osascript",
            "-e", "on run argv",
            "-e", 'display notification (item 2 of argv) with title (item 1 of argv) sound name "Glass"',
            "-e", "end run",
            title,
            body,
        ],
        check=True,
        capture_output=True,
        timeout=10,
    )


def _message(connection: sqlite3.Connection, episode: sqlite3.Row) -> tuple[str, str]:
    first = connection.execute(
        """
        SELECT o.* FROM episode_observations eo JOIN observations o ON o.id = eo.observation_id
        WHERE eo.episode_id = ? ORDER BY eo.lag_s LIMIT 1
        """,
        (episode["id"],),
    ).fetchone()
    title = f"{episode['watch_item']} · {episode['retailer'] or 'unknown retailer'}"
    parts = [SIGNAL_LABELS.get(first["signal"], first["signal"])]
    if first["price"] is not None:
        parts.append(f"${first['price']:,.2f}")
    parts.append(f"via {first['source_id']}")
    body = " · ".join(parts) + f"\n{(first['product_text'] or first['text'])[:140]}"
    return title, body


def maybe_notify(
    connection: sqlite3.Connection,
    episode_id: int,
    *,
    now: dt.datetime,
    send: Sender = macos_notify,
    watch: Iterable[WatchItem] | None = None,
) -> bool:
    episode = connection.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
    if episode is None or not episode["watch_item"] or episode["family"] != "availability":
        return False
    if now - dt.datetime.fromisoformat(episode["opened_at"]) > MAX_AGE:
        return False

    thresholds = {item.name: item.alert_at for item in (watch if watch is not None else watchlist.load())}
    prices = [
        row["price"]
        for row in connection.execute(
            "SELECT o.price FROM episode_observations eo JOIN observations o ON o.id = eo.observation_id "
            "WHERE eo.episode_id = ? AND o.price IS NOT NULL",
            (episode_id,),
        )
    ]
    limit = thresholds.get(episode["watch_item"])
    if prices and limit is not None and min(prices) > limit:
        return False

    title, body = _message(connection, episode)
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO notifications (dedupe_key, episode_id, channel, title, body, created_at, status)
        VALUES (?, ?, 'macos', ?, ?, ?, 'sent')
        """,
        (f"episode:{episode_id}", episode_id, title, body, iso(now)),
    )
    connection.commit()
    if not cursor.rowcount:
        return False
    try:
        send(title, body)
    except Exception as exc:  # a failed banner must not break ingestion
        connection.execute(
            "UPDATE notifications SET status = 'failed', error = ? WHERE dedupe_key = ?",
            (f"{type(exc).__name__}: {exc}"[:300], f"episode:{episode_id}"),
        )
        connection.commit()
        return False
    return True
