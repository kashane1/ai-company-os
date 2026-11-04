"""Sync current sealed products from tcgcsv and emit "when" events.

A group (set) is refreshed when it is recent or upcoming, or when a watched
item names it. Its product list is re-fetched only when tcgcsv's modifiedOn
changes; prices are recorded once per day for every selected group.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from typing import Iterable, Protocol

from .. import sources, watchlist
from ..config import CATALOG_WINDOW_DAYS
from ..db import iso, record_event
from . import classify

SOURCE_ID = "tcgcsv"
# tcgcsv's catch-all group for sealed products outside a set. It is undated,
# so it is always checked and its products are dated only by presale info.
ALWAYS_INCLUDE_GROUPS = frozenset({"Miscellaneous Cards & Products"})


class CatalogClient(Protocol):
    def fetch_groups(self) -> list[dict]: ...
    def fetch_products(self, group_id: int) -> list[dict]: ...
    def fetch_prices(self, group_id: int) -> list[dict]: ...


@dataclass
class CatalogSyncResult:
    groups_selected: int = 0
    groups_refetched: int = 0
    products_upserted: int = 0
    singles_skipped: int = 0
    prices_recorded: int = 0
    events_emitted: int = 0


def select_groups(
    groups: Iterable[dict],
    *,
    today: dt.date,
    window_days: int,
    watch_set_keys: Iterable[str],
) -> list[dict]:
    earliest = (today - dt.timedelta(days=window_days)).isoformat()
    keys = set(watch_set_keys)
    selected = []
    for group in groups:
        name = group.get("name") or ""
        published = classify.known_date(group.get("publishedOn"))
        recent = published is not None and published >= earliest
        if recent or name in ALWAYS_INCLUDE_GROUPS or classify.set_key(name) in keys:
            selected.append(group)
    return selected


def _upsert_group(connection: sqlite3.Connection, group: dict) -> str | None:
    """Store group metadata; returns the modifiedOn of its last product sync."""
    previous = connection.execute(
        "SELECT products_synced_modified_on FROM catalog_groups WHERE group_id = ?",
        (group["groupId"],),
    ).fetchone()
    connection.execute(
        """
        INSERT INTO catalog_groups (group_id, name, abbreviation, published_on, modified_on)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(group_id) DO UPDATE SET
            name = excluded.name,
            abbreviation = excluded.abbreviation,
            published_on = excluded.published_on,
            modified_on = excluded.modified_on
        """,
        (
            group["groupId"],
            group.get("name") or f"Group {group['groupId']}",
            group.get("abbreviation"),
            classify.known_date(group.get("publishedOn")),
            group.get("modifiedOn"),
        ),
    )
    return previous["products_synced_modified_on"] if previous else None


def _sync_products(
    connection: sqlite3.Connection,
    group: dict,
    products: list[dict],
    *,
    now: dt.datetime,
    emit: bool,
    result: CatalogSyncResult,
) -> None:
    group_release = classify.known_date(group.get("publishedOn"))
    for product in products:
        if not classify.is_sealed(product):
            result.singles_skipped += 1
            continue
        product_id = int(product["productId"])
        name = product.get("name") or f"Product {product_id}"
        presale = product.get("presaleInfo") or {}
        release_on = classify.known_date(presale.get("releasedOn")) or group_release
        existing = connection.execute(
            "SELECT release_on FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()

        connection.execute(
            """
            INSERT INTO products
                (product_id, group_id, name, product_type, exclusive_retailer, release_on,
                 is_presale, url, first_seen_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                group_id = excluded.group_id,
                name = excluded.name,
                product_type = excluded.product_type,
                exclusive_retailer = excluded.exclusive_retailer,
                release_on = excluded.release_on,
                is_presale = excluded.is_presale,
                url = excluded.url,
                updated_at = excluded.updated_at
            """,
            (
                product_id,
                int(group["groupId"]),
                name,
                classify.product_type(name),
                classify.exclusive_retailer(name),
                release_on,
                1 if presale.get("isPresale") else 0,
                product.get("url"),
                iso(now),
                iso(now),
            ),
        )
        result.products_upserted += 1

        if not emit:
            continue
        if existing is None:
            emitted = record_event(
                connection,
                source_id=SOURCE_ID,
                kind="sku_added",
                subject_key=str(product_id),
                subject_text=name,
                product_id=product_id,
                now=now,
            )
        elif existing["release_on"] != release_on:
            emitted = record_event(
                connection,
                source_id=SOURCE_ID,
                kind="release_date_changed",
                subject_key=str(product_id),
                subject_text=name,
                value=f"{existing['release_on']} -> {release_on}",
                product_id=product_id,
                now=now,
            )
        else:
            emitted = False
        result.events_emitted += int(emitted)


def _record_prices(
    connection: sqlite3.Connection,
    group_id: int,
    prices: list[dict],
    *,
    day: str,
    result: CatalogSyncResult,
) -> None:
    sealed_ids = {
        row["product_id"]
        for row in connection.execute("SELECT product_id FROM products WHERE group_id = ?", (group_id,))
    }
    for row in prices:
        product_id = row.get("productId")
        if product_id not in sealed_ids or row.get("marketPrice") is None:
            continue
        connection.execute(
            """
            INSERT INTO price_points (product_id, day, market_price, low_price)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(product_id, day) DO UPDATE SET
                market_price = excluded.market_price,
                low_price = excluded.low_price
            """,
            (product_id, day, row.get("marketPrice"), row.get("lowPrice")),
        )
        result.prices_recorded += 1


def sync_catalog(
    connection: sqlite3.Connection,
    client: CatalogClient,
    *,
    now: dt.datetime,
    watch_set_keys: Iterable[str] | None = None,
    window_days: int = CATALOG_WINDOW_DAYS,
) -> CatalogSyncResult:
    result = CatalogSyncResult()
    emit = sources.has_succeeded(connection, SOURCE_ID)
    groups = client.fetch_groups()
    if watch_set_keys is None:
        watch_set_keys = watchlist.set_keys_for(
            (group.get("name") or "" for group in groups),
            (item.name for item in watchlist.load()),
        )
    selected = select_groups(groups, today=now.date(), window_days=window_days, watch_set_keys=watch_set_keys)
    result.groups_selected = len(selected)

    for group in selected:
        group_id = int(group["groupId"])
        synced_modified_on = _upsert_group(connection, group)
        if synced_modified_on is None or synced_modified_on != group.get("modifiedOn"):
            _sync_products(connection, group, client.fetch_products(group_id), now=now, emit=emit, result=result)
            connection.execute(
                "UPDATE catalog_groups SET products_synced_modified_on = ? WHERE group_id = ?",
                (group.get("modifiedOn"), group_id),
            )
            result.groups_refetched += 1
        _record_prices(connection, group_id, client.fetch_prices(group_id), day=now.date().isoformat(), result=result)
        connection.commit()
    return result
