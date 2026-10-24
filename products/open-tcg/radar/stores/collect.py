"""Poll the store registry and keep listing history. Collection only.

Each due store is fetched on a worker thread (one request at a time per
host); results are written here on the calling thread. A store's first full
sweep is its silent baseline. Later runs record a snapshot row only when a
listing appears or its price or availability changes. Nothing here creates
observations, episodes or notifications.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Callable

import httpx

from ..config import (
    STORE_FETCH_WORKERS,
    STORE_FULL_SWEEP_EVERY_S,
    STORE_FULL_SWEEP_MAX_PAGES,
    STORE_ROBOTS_EVERY_S,
)
from ..db import iso
from ..http import make_client
from . import match, registry
from .shopify import FetchResult, StoreFetchError, StoreReader

SOURCE_ID = "stores"


@dataclass
class StorePlan:
    store: registry.Store
    is_full_sweep: bool
    is_robots_check_due: bool


@dataclass
class StoreOutcome:
    plan: StorePlan
    result: FetchResult | None = None
    is_robots_allowed: bool | None = None
    error: str | None = None


@dataclass
class CollectSummary:
    stores_polled: int = 0
    stores_failed: int = 0
    full_sweeps: int = 0
    listings_new: int = 0
    listings_changed: int = 0
    failures: list[str] = field(default_factory=list)


def _cents(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        cents = Decimal(str(value)) * 100
    except InvalidOperation:
        return None
    return int(cents) if cents > 0 else None


def _age_exceeds(value: str | None, now: dt.datetime, seconds: int) -> bool:
    if not value:
        return True
    return now - dt.datetime.fromisoformat(value) >= dt.timedelta(seconds=seconds)


def sync_registry(connection: sqlite3.Connection, stores: list[registry.Store]) -> None:
    connection.executemany(
        """
        INSERT INTO stores (store_id, name, domain, platform, tier, trust)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(store_id) DO UPDATE SET
            name = excluded.name, domain = excluded.domain, platform = excluded.platform,
            tier = excluded.tier, trust = excluded.trust
        """,
        [(s.store_id, s.name, s.domain, s.platform, s.tier, s.trust) for s in stores],
    )
    connection.commit()


def plan(connection: sqlite3.Connection, stores: list[registry.Store], now: dt.datetime) -> list[StorePlan]:
    """Every polled store gets a discovery read; a full sweep once a day."""
    plans = []
    for store in stores:
        if not store.is_polled:
            continue
        row = connection.execute(
            "SELECT last_full_sweep_at, robots_checked_at, is_robots_allowed FROM stores WHERE store_id = ?",
            (store.store_id,),
        ).fetchone()
        plans.append(
            StorePlan(
                store=store,
                is_full_sweep=_age_exceeds(row["last_full_sweep_at"], now, STORE_FULL_SWEEP_EVERY_S),
                is_robots_check_due=row["is_robots_allowed"] is None
                or _age_exceeds(row["robots_checked_at"], now, STORE_ROBOTS_EVERY_S),
            )
        )
    return plans


def fetch(plan_item: StorePlan, reader: StoreReader) -> StoreOutcome:
    outcome = StoreOutcome(plan=plan_item)
    try:
        if plan_item.is_robots_check_due:
            outcome.is_robots_allowed = reader.robots_allows_products()
            if not outcome.is_robots_allowed:
                return outcome
        max_pages = STORE_FULL_SWEEP_MAX_PAGES if plan_item.is_full_sweep else 1
        outcome.result = reader.fetch(max_pages=max_pages)
    except StoreFetchError as exc:
        outcome.error = str(exc)
    return outcome


def _snapshot_change(previous: sqlite3.Row, price_cents: int | None, is_available: bool) -> str | None:
    price_changed = previous["price_cents"] != price_cents
    availability_changed = bool(previous["is_available"]) != is_available
    if price_changed and availability_changed:
        return "price_and_availability"
    if price_changed:
        return "price"
    if availability_changed:
        return "availability"
    return None


def persist(
    connection: sqlite3.Connection,
    store: registry.Store,
    products: list[dict],
    catalog: match.Catalog,
    *,
    now: dt.datetime,
    is_baseline: bool,
) -> tuple[int, int]:
    """Upsert the store's non-excluded Pokémon listings; returns (new, changed)."""
    new_count = 0
    changed_count = 0
    stamp = iso(now)
    for product in products:
        if not match.is_pokemon(product):
            continue
        for variant in product.get("variants") or []:
            variant_id = variant.get("id")
            if not isinstance(variant_id, int):
                continue
            price_cents = _cents(variant.get("price"))
            compare_at_cents = _cents(variant.get("compare_at_price"))
            is_available = bool(variant.get("available"))
            result = match.match_listing(catalog, product.get("title") or "", variant.get("title"))
            # Singles, graded cards, non-English products and the like are
            # most of a store's catalog and never relevant, so they aren't kept.
            if result.status == "excluded":
                continue
            previous = connection.execute(
                "SELECT price_cents, is_available FROM store_listings WHERE store_id = ? AND variant_id = ?",
                (store.store_id, variant_id),
            ).fetchone()
            handle = product.get("handle") or ""
            values = {
                "store_id": store.store_id,
                "variant_id": variant_id,
                "shop_product_id": product.get("id") or 0,
                "handle": handle,
                "title": product.get("title") or "",
                "variant_title": variant.get("title"),
                "vendor": product.get("vendor"),
                "url": f"{store.base_url}/products/{handle}?variant={variant_id}",
                "listed_at": product.get("created_at"),
                "now": stamp,
                "is_baseline": 1 if is_baseline else 0,
                "price_cents": price_cents,
                "compare_at_cents": compare_at_cents,
                "is_available": 1 if is_available else 0,
                "language": result.language,
                "match_status": result.status,
                "match_reason": result.reason,
                "catalog_product_id": result.catalog_product_id,
            }
            connection.execute(
                """
                INSERT INTO store_listings (
                    store_id, variant_id, shop_product_id, handle, title, variant_title, vendor, url,
                    listed_at, first_seen_at, last_seen_at, is_baseline, price_cents, compare_at_cents,
                    is_available, language, match_status, match_reason, catalog_product_id)
                VALUES (
                    :store_id, :variant_id, :shop_product_id, :handle, :title, :variant_title, :vendor, :url,
                    :listed_at, :now, :now, :is_baseline, :price_cents, :compare_at_cents,
                    :is_available, :language, :match_status, :match_reason, :catalog_product_id)
                ON CONFLICT(store_id, variant_id) DO UPDATE SET
                    shop_product_id = excluded.shop_product_id, handle = excluded.handle,
                    title = excluded.title, variant_title = excluded.variant_title,
                    vendor = excluded.vendor, url = excluded.url, listed_at = excluded.listed_at,
                    last_seen_at = excluded.last_seen_at, price_cents = excluded.price_cents,
                    compare_at_cents = excluded.compare_at_cents, is_available = excluded.is_available,
                    language = excluded.language, match_status = excluded.match_status,
                    match_reason = excluded.match_reason, catalog_product_id = excluded.catalog_product_id
                """,
                values,
            )
            if previous is None:
                change = "first_seen"
                if not is_baseline:
                    new_count += 1
            else:
                change = _snapshot_change(previous, price_cents, is_available)
                if change:
                    changed_count += 1
            if change:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO listing_snapshots
                        (store_id, variant_id, observed_at, change, price_cents, compare_at_cents, is_available)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (store.store_id, variant_id, stamp, change, price_cents, compare_at_cents, values["is_available"]),
                )
    return new_count, changed_count


def _record_store(connection: sqlite3.Connection, outcome: StoreOutcome, now: dt.datetime) -> None:
    stamp = iso(now)
    store_id = outcome.plan.store.store_id
    if outcome.is_robots_allowed is not None:
        connection.execute(
            "UPDATE stores SET robots_checked_at = ?, is_robots_allowed = ? WHERE store_id = ?",
            (stamp, 1 if outcome.is_robots_allowed else 0, store_id),
        )
    if outcome.error or outcome.result is None:
        error = outcome.error or "robots.txt disallows /products.json"
        connection.execute(
            """
            UPDATE stores SET last_error = ?, consecutive_failures = consecutive_failures + 1
            WHERE store_id = ?
            """,
            (error[:500], store_id),
        )
        return
    connection.execute(
        "UPDATE stores SET last_discovery_at = ?, last_success_at = ?, last_error = NULL, "
        "consecutive_failures = 0 WHERE store_id = ?",
        (stamp, stamp, store_id),
    )
    if outcome.plan.is_full_sweep:
        connection.execute(
            """
            UPDATE stores SET last_full_sweep_at = ?, baseline_at = COALESCE(baseline_at, ?),
                last_sweep_pages = ?, is_last_sweep_truncated = ?
            WHERE store_id = ?
            """,
            (stamp, stamp, outcome.result.pages_fetched, 1 if outcome.result.is_truncated else 0, store_id),
        )


def collect(
    connection: sqlite3.Connection,
    *,
    now: dt.datetime,
    stores: list[registry.Store] | None = None,
    make_reader: Callable[[registry.Store, httpx.Client], StoreReader] = StoreReader,
    client_factory: Callable[[], httpx.Client] = make_client,
    workers: int = STORE_FETCH_WORKERS,
) -> CollectSummary:
    stores = registry.load() if stores is None else stores
    sync_registry(connection, stores)
    plans = plan(connection, stores, now)
    catalog = match.Catalog.from_db(connection)
    summary = CollectSummary()

    def run(plan_item: StorePlan) -> StoreOutcome:
        with client_factory() as client:
            return fetch(plan_item, make_reader(plan_item.store, client))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        outcomes = list(pool.map(run, plans))

    for outcome in outcomes:
        store = outcome.plan.store
        summary.stores_polled += 1
        if outcome.result is not None:
            baseline_row = connection.execute(
                "SELECT baseline_at FROM stores WHERE store_id = ?", (store.store_id,)
            ).fetchone()
            new, changed = persist(
                connection,
                store,
                outcome.result.products,
                catalog,
                now=now,
                is_baseline=baseline_row["baseline_at"] is None,
            )
            summary.listings_new += new
            summary.listings_changed += changed
            if outcome.plan.is_full_sweep:
                summary.full_sweeps += 1
        else:
            summary.stores_failed += 1
            summary.failures.append(f"{store.store_id}: {outcome.error or 'robots.txt disallows'}")
        _record_store(connection, outcome, now)
        connection.commit()
    return summary


def rematch(connection: sqlite3.Connection) -> int:
    """Re-run matching on stored listings, e.g. after the catalog grows."""
    catalog = match.Catalog.from_db(connection)
    rows = connection.execute("SELECT store_id, variant_id, title, variant_title FROM store_listings").fetchall()
    for row in rows:
        result = match.match_listing(catalog, row["title"], row["variant_title"])
        connection.execute(
            """
            UPDATE store_listings SET language = ?, match_status = ?, match_reason = ?, catalog_product_id = ?
            WHERE store_id = ? AND variant_id = ?
            """,
            (result.language, result.status, result.reason, result.catalog_product_id, row["store_id"], row["variant_id"]),
        )
    connection.commit()
    return len(rows)
