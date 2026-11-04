"""Database access: the inventory store, plus the catalog attached read-only.

Two databases, on purpose.

`inventory.db` is source of truth — what you own, what you paid, where it is.
Nothing can rebuild it.

`pokemon.db` belongs to the sibling pokemon-tcg-search project: 27k cards, 41k
variants and ~36M daily TCGplayer price observations, refreshed by its own cron.
It is derived data with a `make clean-db` target that deletes it. Keeping the
two in one file would put the irreplaceable half one command away from gone, so
the catalog is attached read-only and joined on product_id / variant_id.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# INVENTORY_DB lets you point the CLI at a scratch database (data/demo.db, a
# test fixture) without risking the real one.
INVENTORY_DB = Path(
    os.environ.get("INVENTORY_DB") or PROJECT_ROOT / "data" / "inventory.db"
)
DEFAULT_CATALOG_DB = Path(
    os.environ.get("CATALOG_DB")
    or PROJECT_ROOT.parent / "pokemon-tcg-search" / "data" / "pokemon.db"
)

_SCHEMA = Path(__file__).resolve().parent / "schema.sql"
_VIEWS = Path(__file__).resolve().parent / "views.sql"
_SEED = Path(__file__).resolve().parent / "seed.sql"

# Columns added after the first databases were created. ALTER TABLE ADD COLUMN
# is the one schema change SQLite applies cheaply to a populated table, so
# additive migrations are the only kind this project does; anything structural
# would need a rebuild and is not worth the risk against source-of-truth data.
_COLUMN_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("channels", "small_order_fee_cents", "INTEGER"),
    ("channels", "small_order_max_cents", "INTEGER"),
    ("channels", "free_listings_per_period", "INTEGER"),
    ("channels", "insertion_fee_cents", "INTEGER NOT NULL DEFAULT 0"),
    ("listings", "listing_title", "TEXT"),
)


class CatalogUnavailable(RuntimeError):
    """The catalog database could not be attached."""


def connect(
    inventory_path: Path | None = None,
    catalog_path: Path | None = None,
    *,
    with_catalog: bool = True,
) -> sqlite3.Connection:
    """Open the inventory database, with the catalog attached as `catalog`."""
    inventory_path = Path(inventory_path or INVENTORY_DB)
    inventory_path.parent.mkdir(parents=True, exist_ok=True)

    # uri=True on the main connection is what makes SQLite honor the
    # `?mode=ro` URI in the ATTACH below; without it the attach fails outright.
    conn = sqlite3.connect(f"file:{inventory_path}", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    if with_catalog:
        attach_catalog(conn, catalog_path)
    return conn


def attach_catalog(conn: sqlite3.Connection, catalog_path: Path | None = None) -> None:
    """Attach the price catalog read-only.

    `mode=ro` is what keeps an inventory bug from corrupting 971 days of price
    history that takes ~15 minutes to rebuild. If the read-only attach fails we
    raise rather than silently falling back to a writable one — a writable
    catalog is the failure we are trying to prevent.
    """
    catalog_path = Path(catalog_path or DEFAULT_CATALOG_DB).resolve()
    if not catalog_path.exists():
        raise CatalogUnavailable(
            f"No catalog database at {catalog_path}. "
            "Build it with: cd ../pokemon-tcg-search && make build"
        )

    uri = f"file:{catalog_path}?mode=ro"
    try:
        conn.execute("ATTACH DATABASE ? AS catalog", (uri,))
    except sqlite3.OperationalError as exc:
        raise CatalogUnavailable(f"Could not attach {catalog_path} read-only: {exc}") from exc


def initialize(conn: sqlite3.Connection) -> None:
    """Create tables, apply migrations, rebuild views and seed. Idempotent.

    The schema runs only on a fresh database, so a real mismatch between this
    file and an existing database still raises rather than being papered over
    by IF NOT EXISTS. Views are derived, so they are dropped and recreated
    every time — that is how a view change reaches an existing database. The
    seed is OR IGNORE throughout and always runs, which adds newly introduced
    reference rows without overwriting tuned ones.
    """
    if not is_initialized(conn):
        conn.executescript(_SCHEMA.read_text())
    migrate(conn)
    conn.executescript(_VIEWS.read_text())
    conn.executescript(_SEED.read_text())
    conn.commit()


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Bring an existing database up to the current schema. Returns what ran."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name       TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    applied: list[str] = []

    for table, column, ddl in _COLUMN_MIGRATIONS:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            applied.append(f"{table}.{column}")

    applied.extend(_apply_once(conn, _verified_channel_economics))
    conn.commit()
    return applied


def _apply_once(conn: sqlite3.Connection, migration) -> list[str]:
    """Run a data migration if it has not run on this database before."""
    name = migration.__name__.lstrip("_")
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE name = ?", (name,)
    ).fetchone()
    if row is not None:
        return []
    migration(conn)
    conn.execute("INSERT INTO schema_migrations (name) VALUES (?)", (name,))
    return [name]


def _verified_channel_economics(conn: sqlite3.Connection) -> None:
    """Replace the originally guessed channel economics with read values.

    The first seed carried estimates for anything that could not be looked up
    without an account. On 2026-11-02 the real numbers were read off the
    published fee schedules and Seller Hub, and the eBay caps turned out to be
    wrong by two orders of magnitude — 5,000 items and $50,000 a month, not 10
    items and $500. The selector solves against these, so the old values were
    quietly throwing away most of the available eBay exposure.

    Rows are only corrected where they still hold the exact original estimate,
    so a value tuned by hand in the meantime is left alone.
    """
    conn.execute(
        """
        UPDATE channels
           SET max_listing_count        = 5000,
               max_listed_value_cents   = 5000000,
               order_fee_cents          = 40,
               small_order_fee_cents    = 30,
               small_order_max_cents    = 1000,
               free_listings_per_period = 250,
               insertion_fee_cents      = 35
         WHERE channel = 'ebay'
           AND max_listing_count      = 10
           AND max_listed_value_cents = 50000
        """
    )
    conn.execute(
        """
        UPDATE channels
           SET free_listings_per_period = NULL,
               insertion_fee_cents      = 0
         WHERE channel = 'tcgplayer'
        """
    )


def is_initialized(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'copies'"
    ).fetchone()
    return row is not None


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str, note: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO settings (key, value, note) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value, note),
    )
    conn.commit()
