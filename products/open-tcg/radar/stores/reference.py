"""Reference catalog for store matching: every English group's sealed products.

The radar's own catalog (`catalog_groups`, `products`) holds only recent and
watched sets because it drives the calendar, Bluesky set detection and alert
text. Store listings span every era, so matching reads this wider copy
instead. It is silent: no calendar events, and the radar tables are untouched.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from ..catalog import classify
from ..catalog.sync import CatalogClient
from ..db import iso

SOURCE_ID = "tcgcsv_reference"
# Older sets' prices move slowly; refresh them weekly instead of daily.
RECENT_GROUP_DAYS = 3 * 365
OLD_GROUP_PRICE_EVERY_DAYS = 7


@dataclass
class ReferenceSyncResult:
    groups_seen: int = 0
    groups_refetched: int = 0
    products_upserted: int = 0
    price_groups: int = 0
    prices_recorded: int = 0


def _prices_due(row: sqlite3.Row | None, group: dict, today: dt.date) -> bool:
    if row is None or not row["prices_day"]:
        return True
    last = dt.date.fromisoformat(row["prices_day"])
    published = classify.known_date(group.get("publishedOn"))
    is_recent = published is None or dt.date.fromisoformat(published) >= today - dt.timedelta(days=RECENT_GROUP_DAYS)
    every_days = 1 if is_recent else OLD_GROUP_PRICE_EVERY_DAYS
    return (today - last).days >= every_days


def _sync_products(connection: sqlite3.Connection, group: dict, products: list[dict], now: dt.datetime) -> int:
    group_id = int(group["groupId"])
    group_release = classify.known_date(group.get("publishedOn"))
    count = 0
    for product in products:
        if not classify.is_sealed(product):
            continue
        name = product.get("name") or f"Product {product['productId']}"
        presale = product.get("presaleInfo") or {}
        connection.execute(
            """
            INSERT INTO ref_products
                (product_id, group_id, name, product_type, exclusive_retailer, release_on, url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                group_id = excluded.group_id, name = excluded.name, product_type = excluded.product_type,
                exclusive_retailer = excluded.exclusive_retailer, release_on = excluded.release_on,
                url = excluded.url, updated_at = excluded.updated_at
            """,
            (
                int(product["productId"]),
                group_id,
                name,
                classify.product_type(name),
                classify.exclusive_retailer(name),
                classify.known_date(presale.get("releasedOn")) or group_release,
                product.get("url"),
                iso(now),
            ),
        )
        count += 1
    return count


def _record_prices(connection: sqlite3.Connection, group_id: int, prices: list[dict], day: str) -> int:
    sealed_ids = {
        row["product_id"]
        for row in connection.execute("SELECT product_id FROM ref_products WHERE group_id = ?", (group_id,))
    }
    count = 0
    for row in prices:
        product_id = row.get("productId")
        if product_id not in sealed_ids or row.get("marketPrice") is None:
            continue
        connection.execute(
            """
            INSERT INTO ref_price_points (product_id, day, market_price, low_price) VALUES (?, ?, ?, ?)
            ON CONFLICT(product_id, day) DO UPDATE SET
                market_price = excluded.market_price, low_price = excluded.low_price
            """,
            (product_id, day, row.get("marketPrice"), row.get("lowPrice")),
        )
        count += 1
    return count


def sync_reference(connection: sqlite3.Connection, client: CatalogClient, *, now: dt.datetime) -> ReferenceSyncResult:
    result = ReferenceSyncResult()
    today = now.date()
    for group in client.fetch_groups():
        group_id = int(group["groupId"])
        result.groups_seen += 1
        row = connection.execute(
            "SELECT products_synced_modified_on, prices_day FROM ref_groups WHERE group_id = ?", (group_id,)
        ).fetchone()
        connection.execute(
            """
            INSERT INTO ref_groups (group_id, name, abbreviation, published_on, modified_on)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(group_id) DO UPDATE SET
                name = excluded.name, abbreviation = excluded.abbreviation,
                published_on = excluded.published_on, modified_on = excluded.modified_on
            """,
            (
                group_id,
                group.get("name") or f"Group {group_id}",
                group.get("abbreviation"),
                classify.known_date(group.get("publishedOn")),
                group.get("modifiedOn"),
            ),
        )
        if row is None or row["products_synced_modified_on"] != group.get("modifiedOn"):
            result.products_upserted += _sync_products(connection, group, client.fetch_products(group_id), now)
            connection.execute(
                "UPDATE ref_groups SET products_synced_modified_on = ? WHERE group_id = ?",
                (group.get("modifiedOn"), group_id),
            )
            result.groups_refetched += 1
        has_products = connection.execute(
            "SELECT 1 FROM ref_products WHERE group_id = ? LIMIT 1", (group_id,)
        ).fetchone()
        if has_products and _prices_due(row, group, today):
            result.prices_recorded += _record_prices(
                connection, group_id, client.fetch_prices(group_id), today.isoformat()
            )
            connection.execute("UPDATE ref_groups SET prices_day = ? WHERE group_id = ?", (today.isoformat(), group_id))
            result.price_groups += 1
        connection.commit()
    return result
