"""Source registry and per-source health.

Every source the radar reads is declared here with its tier and cadence, so
nothing polls a host that is not listed. Health is derived from the last run:
a source that has not succeeded within three cadences is reported as stale.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from .db import iso

STALE_AFTER_CADENCES = 3


@dataclass(frozen=True)
class Source:
    source_id: str
    tier: str  # 'S' shippable candidate, 'L' lab-only
    kind: str
    cadence_s: int
    enabled: bool = True
    note: str = ""


REGISTRY: tuple[Source, ...] = (
    Source("tcgcsv", "S", "poll", 24 * 3600, note="TCGplayer catalog mirror; rebuilt ~20:00 UTC daily"),
    Source("southern_hobby", "L", "poll", 24 * 3600, note="Distributor release and order-due list"),
    Source("pokebeach_rss", "L", "poll", 15 * 60, note="Front-page news RSS"),
    Source(
        "pokemon_news",
        "S",
        "poll",
        24 * 3600,
        enabled=False,
        note="Disabled: pokemon.com serves an Incapsula bot challenge to non-browser clients; not bypassed",
    ),
)

_BY_ID = {source.source_id: source for source in REGISTRY}


def get(source_id: str) -> Source:
    return _BY_ID[source_id]


@dataclass(frozen=True)
class Health:
    source_id: str
    tier: str
    kind: str
    cadence_s: int
    enabled: bool
    note: str
    status: str  # ok | stale | failing | never_run | disabled
    last_success_at: str | None
    last_error: str | None
    consecutive_failures: int


def ensure_registered(connection: sqlite3.Connection) -> None:
    """Upsert registry metadata while keeping each source's run history."""
    connection.executemany(
        """
        INSERT INTO sources (source_id, tier, kind, cadence_s, enabled, note)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            tier = excluded.tier,
            kind = excluded.kind,
            cadence_s = excluded.cadence_s,
            enabled = excluded.enabled,
            note = excluded.note
        """,
        [(s.source_id, s.tier, s.kind, s.cadence_s, 1 if s.enabled else 0, s.note) for s in REGISTRY],
    )
    connection.commit()


def record_run(
    connection: sqlite3.Connection,
    source_id: str,
    *,
    ok: bool,
    now: dt.datetime,
    error: str | None = None,
) -> None:
    if ok:
        connection.execute(
            """
            UPDATE sources
            SET last_run_at = ?, last_success_at = ?, last_error = NULL, consecutive_failures = 0
            WHERE source_id = ?
            """,
            (iso(now), iso(now), source_id),
        )
    else:
        connection.execute(
            """
            UPDATE sources
            SET last_run_at = ?, last_error = ?, consecutive_failures = consecutive_failures + 1
            WHERE source_id = ?
            """,
            (iso(now), (error or "unknown error")[:500], source_id),
        )
    connection.commit()


def has_succeeded(connection: sqlite3.Connection, source_id: str) -> bool:
    """False until a source's first successful run.

    Detectors use this as the bootstrap boundary: the first run records a
    silent baseline, so an empty database does not report every existing item
    as "new".
    """
    row = connection.execute(
        "SELECT last_success_at FROM sources WHERE source_id = ?", (source_id,)
    ).fetchone()
    return bool(row and row["last_success_at"])


def _status(row: sqlite3.Row, now: dt.datetime) -> str:
    if not row["enabled"]:
        return "disabled"
    if row["consecutive_failures"]:
        return "failing"
    if not row["last_success_at"]:
        return "never_run"
    last_success = dt.datetime.fromisoformat(row["last_success_at"])
    if (now - last_success).total_seconds() > row["cadence_s"] * STALE_AFTER_CADENCES:
        return "stale"
    return "ok"


def health(connection: sqlite3.Connection, now: dt.datetime) -> list[Health]:
    rows = connection.execute("SELECT * FROM sources ORDER BY source_id").fetchall()
    return [
        Health(
            source_id=row["source_id"],
            tier=row["tier"],
            kind=row["kind"],
            cadence_s=row["cadence_s"],
            enabled=bool(row["enabled"]),
            note=row["note"] or "",
            status=_status(row, now),
            last_success_at=row["last_success_at"],
            last_error=row["last_error"],
            consecutive_failures=row["consecutive_failures"],
        )
        for row in rows
    ]
