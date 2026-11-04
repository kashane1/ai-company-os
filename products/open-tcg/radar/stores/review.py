"""Review queue and remembered decisions for store listings.

The matcher is conservative, so plausible sealed listings it can't pin down
land in a queue. A decision (confirm a product, or reject the listing) is
stored per store variant and overrides automatic matching from then on.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass, field

from ..db import iso
from . import match

# Unknown-form listings are mostly video games, singles and merchandise, so
# they're queued only when asked for.
REVIEW_REASONS = (
    "variant_unclear",
    "unexplained_words",
    "era_name_only",
    "several_sets",
    "quantity_unclear",
    "set_not_in_catalog",
    "form_not_in_set",
    "damaged",
)


def ensure_schema(connection: sqlite3.Connection) -> None:
    """Point `store_listings.catalog_product_id` at the reference catalog.

    P0/P1 databases created the column referencing the radar's `products`
    table. Matches now come from `ref_products`, so the table is rebuilt once
    with the new reference; rows and snapshots are kept.
    """
    targets = {row["table"] for row in connection.execute("PRAGMA foreign_key_list(store_listings)")}
    if "products" not in targets:
        return
    columns = [row["name"] for row in connection.execute("PRAGMA table_info(store_listings)")]
    create_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'store_listings'"
    ).fetchone()["sql"]
    new_sql = create_sql.replace("CREATE TABLE store_listings", "CREATE TABLE store_listings_new", 1).replace(
        "REFERENCES products(product_id)", "REFERENCES ref_products(product_id)"
    )
    column_list = ", ".join(columns)
    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        with connection:
            connection.execute(new_sql)
            connection.execute(f"INSERT INTO store_listings_new ({column_list}) SELECT {column_list} FROM store_listings")
            connection.execute("DROP TABLE store_listings")
            connection.execute("ALTER TABLE store_listings_new RENAME TO store_listings")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS store_listings_product_idx ON store_listings(catalog_product_id)"
            )
    finally:
        connection.execute("PRAGMA foreign_keys = ON")


@dataclass(frozen=True)
class Decision:
    decision: str  # confirm | reject
    catalog_product_id: int | None


def load_decisions(connection: sqlite3.Connection, store_id: str | None = None) -> dict[tuple[str, int], Decision]:
    query = "SELECT store_id, variant_id, decision, catalog_product_id FROM listing_decisions"
    params: tuple = ()
    if store_id is not None:
        query += " WHERE store_id = ?"
        params = (store_id,)
    return {
        (row["store_id"], row["variant_id"]): Decision(row["decision"], row["catalog_product_id"])
        for row in connection.execute(query, params)
    }


def apply(result: match.MatchResult, decision: Decision | None) -> match.MatchResult:
    if decision is None:
        return result
    if decision.decision == "confirm":
        return match.MatchResult(result.language, "confirmed", None, decision.catalog_product_id)
    return match.MatchResult(result.language, "excluded", "reviewed")


class DecisionError(ValueError):
    pass


def decide(
    connection: sqlite3.Connection,
    *,
    store_id: str,
    variant_id: int,
    product: str,
    decided_by: str,
    now: dt.datetime,
    note: str | None = None,
    same_title: bool = False,
) -> int:
    """Record a decision; returns how many listings it now covers.

    `product` is a reference product id, or "reject". With `same_title`, the
    decision is copied to every listing (any store) whose title and variant
    read the same once folded.
    """
    listing = connection.execute(
        "SELECT title, variant_title FROM store_listings WHERE store_id = ? AND variant_id = ?",
        (store_id, variant_id),
    ).fetchone()
    if listing is None:
        raise DecisionError(f"no listing {store_id}:{variant_id}")
    if product == "reject":
        decision, product_id = "reject", None
    else:
        try:
            product_id = int(product)
        except ValueError as exc:
            raise DecisionError("product must be a reference product id or 'reject'") from exc
        if connection.execute("SELECT 1 FROM ref_products WHERE product_id = ?", (product_id,)).fetchone() is None:
            raise DecisionError(f"no reference product {product_id}")
        decision = "confirm"

    targets = [(store_id, variant_id)]
    if same_title:
        key = _title_key(listing["title"], listing["variant_title"])
        targets = [
            (row["store_id"], row["variant_id"])
            for row in connection.execute("SELECT store_id, variant_id, title, variant_title FROM store_listings")
            if _title_key(row["title"], row["variant_title"]) == key
        ]
    stamp = iso(now)
    for target_store, target_variant in targets:
        connection.execute(
            """
            INSERT INTO listing_decisions
                (store_id, variant_id, decision, catalog_product_id, decided_by, decided_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(store_id, variant_id) DO UPDATE SET
                decision = excluded.decision, catalog_product_id = excluded.catalog_product_id,
                decided_by = excluded.decided_by, decided_at = excluded.decided_at, note = excluded.note
            """,
            (target_store, target_variant, decision, product_id, decided_by, stamp, note),
        )
        connection.execute(
            """
            UPDATE store_listings SET match_status = ?, match_reason = ?, catalog_product_id = ?
            WHERE store_id = ? AND variant_id = ?
            """,
            (
                "confirmed" if decision == "confirm" else "excluded",
                None if decision == "confirm" else "reviewed",
                product_id,
                target_store,
                target_variant,
            ),
        )
    connection.commit()
    return len(targets)


def _title_key(title: str, variant_title: str | None) -> str:
    return match.fold(match.listing_text(title, variant_title))


@dataclass
class QueueItem:
    title: str
    variant_title: str | None
    reason: str
    listing_count: int
    in_stock_count: int
    examples: list[str] = field(default_factory=list)  # "store_id:variant_id"
    candidates: list[match.CatalogProduct] = field(default_factory=list)


def queue(
    connection: sqlite3.Connection,
    *,
    limit: int = 30,
    reason: str | None = None,
    include_unknown_form: bool = False,
) -> list[QueueItem]:
    """Undecided English listings worth a look, grouped by identical title."""
    reasons = list(REVIEW_REASONS) + (["unknown_form"] if include_unknown_form else [])
    if reason is not None:
        reasons = [reason]
    placeholders = ", ".join("?" for _ in reasons)
    rows = connection.execute(
        f"""
        SELECT l.store_id, l.variant_id, l.title, l.variant_title, l.match_reason, l.is_available
        FROM store_listings l
        LEFT JOIN listing_decisions d USING (store_id, variant_id)
        WHERE d.store_id IS NULL AND l.language = 'en'
          AND l.match_status IN ('ambiguous', 'unmatched') AND l.match_reason IN ({placeholders})
        """,
        reasons,
    ).fetchall()
    grouped: dict[str, QueueItem] = {}
    for row in rows:
        key = _title_key(row["title"], row["variant_title"])
        item = grouped.get(key)
        if item is None:
            item = grouped[key] = QueueItem(row["title"], row["variant_title"], row["match_reason"], 0, 0)
        item.listing_count += 1
        item.in_stock_count += row["is_available"]
        if len(item.examples) < 3:
            item.examples.append(f"{row['store_id']}:{row['variant_id']}")
    items = sorted(grouped.values(), key=lambda i: (-i.in_stock_count, -i.listing_count, i.title))[:limit]
    catalog = match.Catalog.from_db(connection)
    for item in items:
        item.candidates = match.candidates(catalog, item.title, item.variant_title)
    return items


def render_queue(items: list[QueueItem]) -> str:
    if not items:
        return "Review queue is empty.\n"
    lines = []
    for number, item in enumerate(items, 1):
        variant = "" if not item.variant_title or item.variant_title == "Default Title" else f" || {item.variant_title}"
        lines.append(
            f"{number:>3}. [{item.reason}] {item.title}{variant}  "
            f"({item.listing_count} listings, {item.in_stock_count} in stock; e.g. {', '.join(item.examples)})"
        )
        for product in item.candidates:
            lines.append(f"       {product.product_id:>8}  {product.name}")
    return "\n".join(lines) + "\n"
