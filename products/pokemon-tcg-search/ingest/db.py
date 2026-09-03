"""SQLite connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import DATABASE_PATH, SCHEMA_PATH


def connect(path: Path | None = None, *, read_only: bool = False) -> sqlite3.Connection:
    """Open a tuned connection to the screener database."""
    target = Path(path or DATABASE_PATH)
    if read_only:
        connection = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(target)

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    # 256MB page cache and memory-backed temp tables: the metrics rebuild does
    # a full scan of ~40M observations and thrashes without them.
    connection.execute("PRAGMA cache_size = -262144")
    connection.execute("PRAGMA temp_store = MEMORY")
    if not read_only:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
    return connection


# Bump when card_metrics gains, loses or redefines a column. `CREATE TABLE IF
# NOT EXISTS` silently keeps an outdated table, so the stale one is dropped and
# rebuilt instead. Safe to do freely: card_metrics is derived entirely from
# price_observations, and `python -m ingest metrics` regenerates it in about a
# minute. The expensive tables (catalog, price_observations) are never touched.
DERIVED_SCHEMA_VERSION = 4

_DERIVED_OBJECTS = (
    "DROP VIEW IF EXISTS screener_rows",
    "DROP TABLE IF EXISTS card_metrics",
)

# Catalog columns added after the first build. Unlike card_metrics these cannot
# be dropped and regenerated — re-syncing the catalog is cheap but the table
# also anchors price_observations by product_id. So they are added in place, and
# `python -m ingest sync-catalog` backfills the values.
_CATALOG_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("cards", "hp", "INTEGER"),
    ("cards", "stage", "TEXT"),
    ("cards", "card_class", "TEXT"),
    ("cards", "trainer_kind", "TEXT"),
)


def _migrate_catalog(connection: sqlite3.Connection) -> list[str]:
    """Add any missing catalog columns. Idempotent; returns what it added."""
    added = []
    for table, column, column_type in _CATALOG_MIGRATIONS:
        existing = {
            row[1] for row in connection.execute(f"PRAGMA table_info({table})")
        }
        if not existing:
            continue  # table does not exist yet; schema.sql will create it
        if column not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
            added.append(f"{table}.{column}")
    return added


def apply_schema(connection: sqlite3.Connection) -> None:
    installed = connection.execute("PRAGMA user_version").fetchone()[0]
    if installed < DERIVED_SCHEMA_VERSION:
        for statement in _DERIVED_OBJECTS:
            connection.execute(statement)
        connection.execute(f"PRAGMA user_version = {DERIVED_SCHEMA_VERSION}")

    # Before schema.sql, because its CREATE VIEW references the new columns.
    _migrate_catalog(connection)
    connection.executescript(SCHEMA_PATH.read_text())
    connection.commit()


def open_initialised(path: Path | None = None) -> sqlite3.Connection:
    """Open a writable connection with the schema guaranteed to exist."""
    connection = connect(path)
    apply_schema(connection)
    return connection
