"""SQLite connection and schema setup."""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

from .config import DB_PATH, SCHEMA_PATH


def connect(path: str | Path = DB_PATH) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        connection.execute("PRAGMA journal_mode = WAL")
    return connection


def init(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_PATH.read_text())
    connection.commit()


def iso(moment: dt.datetime) -> str:
    """Timestamps are stored as UTC ISO-8601 strings."""
    return moment.astimezone(dt.timezone.utc).isoformat(timespec="seconds")


def record_event(
    connection: sqlite3.Connection,
    *,
    source_id: str,
    kind: str,
    subject_key: str,
    subject_text: str,
    now: dt.datetime,
    value: str = "",
    product_id: int | None = None,
) -> bool:
    """Insert a calendar event once; returns True only when it is new."""
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO calendar_events
            (source_id, kind, subject_key, subject_text, value, product_id, detected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (source_id, kind, subject_key, subject_text, value, product_id, iso(now)),
    )
    return cursor.rowcount == 1
