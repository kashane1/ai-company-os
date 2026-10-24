"""Poll the store registry and keep listing history. Collection only.

Each due store is fetched on a worker thread (one request at a time per
host); results are written here on the calling thread. Every run reads a
due store's newest catalog page; once a day a full sweep reads its selected
sealed collections, or its whole catalog when none is selected. A store's
first full sweep is its silent baseline. Later runs record a snapshot row only when a
listing appears or its price or availability changes. Nothing here creates
observations, episodes or notifications.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import sqlite3
import threading
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Callable

import httpx

from ..config import (
    STORE_COLLECTIONS_EVERY_S,
    STORE_FETCH_WORKERS,
    STORE_FULL_SWEEP_EVERY_S,
    STORE_FULL_SWEEP_MAX_PAGES,
    STORE_MAX_CATALOG_SWEEPS_PER_RUN,
    STORE_ROBOTS_EVERY_S,
)
from ..db import iso
from ..http import make_client
from . import collections, match, registry, review
from .shopify import StoreFetchError, StoreReader

SOURCE_ID = "stores"
# The sync runs every 15 minutes with some jitter; without slack a store due
# every 15 minutes would skip every other run.
DISCOVERY_SLACK_S = 120


@dataclass
class StorePlan:
    store: registry.Store
    is_discovery_due: bool
    is_full_sweep: bool
    is_robots_check_due: bool
    is_collection_check_due: bool
    selected_collections: tuple[str, ...] = ()


@dataclass
class StoreOutcome:
    plan: StorePlan
    products: list[dict] | None = None
    is_discovery_read: bool = False
    sweep_mode: str | None = None  # 'collections' | 'catalog' when a full sweep ran
    sweep_pages: int = 0
    is_sweep_truncated: bool = False
    collection_check: collections.CollectionCheck | None = None
    is_collection_recheck_needed: bool = False
    is_robots_allowed: bool | None = None
    is_catalog_sweep_deferred: bool = False
    error: str | None = None


class CatalogSweepBudget:
    """Whole-catalog sweeps left this run, shared by the worker threads."""

    def __init__(self, remaining: int):
        self._remaining = remaining
        self._lock = threading.Lock()

    def take(self) -> bool:
        with self._lock:
            if self._remaining <= 0:
                return False
            self._remaining -= 1
            return True


@dataclass
class CollectSummary:
    stores_polled: int = 0
    stores_failed: int = 0
    full_sweeps: int = 0
    collection_checks: int = 0
    catalog_sweeps_deferred: int = 0
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
    """Which stores to read this run and how.

    Newest-page discovery follows each store's cadence, a full sweep is due
    daily, and collection discovery weekly. Whether a due sweep reads
    collections or the whole catalog is settled in `fetch`, after any
    collection check, and catalog sweeps draw on a per-run budget there.
    """
    plans = []
    for store in stores:
        if not store.is_polled:
            continue
        row = connection.execute(
            "SELECT last_discovery_at, last_full_sweep_at, robots_checked_at, is_robots_allowed "
            "FROM stores WHERE store_id = ?",
            (store.store_id,),
        ).fetchone()
        check_row = connection.execute(
            "SELECT checked_at FROM store_collection_checks WHERE store_id = ?", (store.store_id,)
        ).fetchone()
        selected = tuple(
            r["handle"]
            for r in connection.execute(
                "SELECT handle FROM store_collections WHERE store_id = ? AND is_selected = 1 ORDER BY handle",
                (store.store_id,),
            )
        )
        is_discovery_due = _age_exceeds(
            row["last_discovery_at"], now, store.discovery_minutes * 60 - DISCOVERY_SLACK_S
        )
        is_full_sweep = _age_exceeds(row["last_full_sweep_at"], now, STORE_FULL_SWEEP_EVERY_S)
        is_collection_check_due = check_row is None or _age_exceeds(
            check_row["checked_at"], now, STORE_COLLECTIONS_EVERY_S
        )
        if not (is_discovery_due or is_full_sweep or is_collection_check_due):
            continue
        plans.append(
            StorePlan(
                store=store,
                is_discovery_due=is_discovery_due,
                is_full_sweep=is_full_sweep,
                is_robots_check_due=row["is_robots_allowed"] is None
                or _age_exceeds(row["robots_checked_at"], now, STORE_ROBOTS_EVERY_S),
                is_collection_check_due=is_collection_check_due,
                selected_collections=selected,
            )
        )
    return plans


def _sweep_collections(reader: StoreReader, handles: tuple[str, ...] | list[str], outcome: StoreOutcome) -> list[dict]:
    products: list[dict] = []
    for handle in handles:
        result = reader.fetch(max_pages=STORE_FULL_SWEEP_MAX_PAGES, collection=handle)
        products.extend(result.products)
        outcome.sweep_pages += result.pages_fetched
        outcome.is_sweep_truncated = outcome.is_sweep_truncated or result.is_truncated
    return products


def fetch(
    plan_item: StorePlan,
    reader: StoreReader,
    catalog: match.Catalog,
    budget: CatalogSweepBudget | None = None,
) -> StoreOutcome:
    outcome = StoreOutcome(plan=plan_item)
    try:
        if plan_item.is_robots_check_due:
            outcome.is_robots_allowed = reader.robots_allows_products()
            if not outcome.is_robots_allowed:
                return outcome
        selected: tuple[str, ...] | list[str] = plan_item.selected_collections
        if plan_item.is_collection_check_due:
            try:
                outcome.collection_check = collections.check(reader, catalog)
            except StoreFetchError as exc:
                outcome.collection_check = collections.CollectionCheck(error=str(exc))
            if outcome.collection_check.error is None:
                selected = outcome.collection_check.selected_handles

        products: list[dict] = []
        if plan_item.is_full_sweep and selected:
            try:
                products = _sweep_collections(reader, selected, outcome)
                outcome.sweep_mode = "collections"
            except StoreFetchError:
                # A selected collection vanished or broke: sweep the catalog
                # this time and rediscover collections next run.
                outcome.is_collection_recheck_needed = True
                outcome.sweep_pages = 0
                outcome.is_sweep_truncated = False
                products = []
        is_catalog_sweep = plan_item.is_full_sweep and outcome.sweep_mode is None
        if is_catalog_sweep and budget is not None and not budget.take():
            outcome.is_catalog_sweep_deferred = True
            is_catalog_sweep = False
        if is_catalog_sweep:
            result = reader.fetch(max_pages=STORE_FULL_SWEEP_MAX_PAGES)
            products = result.products
            outcome.sweep_mode = "catalog"
            outcome.sweep_pages = result.pages_fetched
            outcome.is_sweep_truncated = result.is_truncated
            outcome.is_discovery_read = True
        if not outcome.is_discovery_read and (plan_item.is_discovery_due or outcome.sweep_mode):
            products = reader.fetch(max_pages=1).products + products
            outcome.is_discovery_read = True
        unique: dict[object, dict] = {}
        for product in products:
            unique.setdefault(product.get("id"), product)
        outcome.products = list(unique.values())
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
    decisions = review.load_decisions(connection, store.store_id)
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
            result = review.apply(result, decisions.get((store.store_id, variant_id)))
            # Singles, graded cards, non-English products and the like are
            # most of a store's catalog and never relevant, so they aren't
            # kept. Listings rejected in review are kept, so the decision sticks.
            if result.status == "excluded" and result.reason != "reviewed":
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


def _record_collections(connection: sqlite3.Connection, store_id: str, check: collections.CollectionCheck, stamp: str) -> None:
    if check.error is None:
        selected = set(check.selected_handles)
        connection.execute("DELETE FROM store_collections WHERE store_id = ?", (store_id,))
        connection.executemany(
            """
            INSERT INTO store_collections
                (store_id, handle, title, sampled_count, sealed_count, is_selected, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (store_id, sample.handle, sample.title, sample.sampled_count, sample.sealed_count,
                 1 if sample.handle in selected else 0, stamp)
                for sample in check.samples
            ],
        )
    connection.execute(
        """
        INSERT INTO store_collection_checks (store_id, checked_at, candidate_count, selected_count, error)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(store_id) DO UPDATE SET
            checked_at = excluded.checked_at, candidate_count = excluded.candidate_count,
            selected_count = excluded.selected_count, error = excluded.error
        """,
        (store_id, stamp, check.candidate_count, len(check.selected_handles), check.error),
    )


def _record_store(connection: sqlite3.Connection, outcome: StoreOutcome, now: dt.datetime) -> None:
    stamp = iso(now)
    store_id = outcome.plan.store.store_id
    if outcome.is_robots_allowed is not None:
        connection.execute(
            "UPDATE stores SET robots_checked_at = ?, is_robots_allowed = ? WHERE store_id = ?",
            (stamp, 1 if outcome.is_robots_allowed else 0, store_id),
        )
    if outcome.collection_check is not None:
        _record_collections(connection, store_id, outcome.collection_check, stamp)
    if outcome.is_collection_recheck_needed:
        connection.execute("DELETE FROM store_collection_checks WHERE store_id = ?", (store_id,))
    if outcome.error or outcome.products is None:
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
        "UPDATE stores SET last_success_at = ?, last_error = NULL, consecutive_failures = 0 WHERE store_id = ?",
        (stamp, store_id),
    )
    if outcome.is_discovery_read:
        connection.execute("UPDATE stores SET last_discovery_at = ? WHERE store_id = ?", (stamp, store_id))
    if outcome.sweep_mode is not None:
        connection.execute(
            """
            UPDATE stores SET last_full_sweep_at = ?, baseline_at = COALESCE(baseline_at, ?),
                last_sweep_pages = ?, is_last_sweep_truncated = ?
            WHERE store_id = ?
            """,
            (stamp, stamp, outcome.sweep_pages, 1 if outcome.is_sweep_truncated else 0, store_id),
        )


def collect(
    connection: sqlite3.Connection,
    *,
    now: dt.datetime,
    stores: list[registry.Store] | None = None,
    make_reader: Callable[[registry.Store, httpx.Client], StoreReader] = StoreReader,
    client_factory: Callable[[], httpx.Client] = make_client,
    workers: int = STORE_FETCH_WORKERS,
    max_catalog_sweeps: int = STORE_MAX_CATALOG_SWEEPS_PER_RUN,
) -> CollectSummary:
    stores = registry.load() if stores is None else stores
    review.ensure_schema(connection)
    sync_registry(connection, stores)
    catalog = match.Catalog.from_db(connection)
    plans = plan(connection, stores, now)
    summary = CollectSummary()
    budget = CatalogSweepBudget(max_catalog_sweeps)

    def run(plan_item: StorePlan) -> StoreOutcome:
        with client_factory() as client:
            return fetch(plan_item, make_reader(plan_item.store, client), catalog, budget)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        outcomes = list(pool.map(run, plans))

    for outcome in outcomes:
        store = outcome.plan.store
        summary.stores_polled += 1
        if outcome.collection_check is not None:
            summary.collection_checks += 1
        if outcome.is_catalog_sweep_deferred:
            summary.catalog_sweeps_deferred += 1
        if outcome.products is not None:
            baseline_row = connection.execute(
                "SELECT baseline_at FROM stores WHERE store_id = ?", (store.store_id,)
            ).fetchone()
            new, changed = persist(
                connection,
                store,
                outcome.products,
                catalog,
                now=now,
                is_baseline=baseline_row["baseline_at"] is None,
            )
            summary.listings_new += new
            summary.listings_changed += changed
            if outcome.sweep_mode is not None:
                summary.full_sweeps += 1
        else:
            summary.stores_failed += 1
            summary.failures.append(f"{store.store_id}: {outcome.error or 'robots.txt disallows'}")
        _record_store(connection, outcome, now)
        connection.commit()
    return summary


def rematch(connection: sqlite3.Connection) -> int:
    """Re-run matching on stored listings, e.g. after the catalog or matcher changes.

    Review decisions still apply. Listings that the matcher now excludes are
    dropped, as a fresh fetch would drop them.
    """
    review.ensure_schema(connection)
    catalog = match.Catalog.from_db(connection)
    decisions = review.load_decisions(connection)
    rows = connection.execute("SELECT store_id, variant_id, title, variant_title FROM store_listings").fetchall()
    for row in rows:
        result = match.match_listing(catalog, row["title"], row["variant_title"])
        result = review.apply(result, decisions.get((row["store_id"], row["variant_id"])))
        if result.status == "excluded" and result.reason != "reviewed":
            connection.execute(
                "DELETE FROM listing_snapshots WHERE store_id = ? AND variant_id = ?", (row["store_id"], row["variant_id"])
            )
            connection.execute(
                "DELETE FROM store_listings WHERE store_id = ? AND variant_id = ?", (row["store_id"], row["variant_id"])
            )
            continue
        connection.execute(
            """
            UPDATE store_listings SET language = ?, match_status = ?, match_reason = ?, catalog_product_id = ?
            WHERE store_id = ? AND variant_id = ?
            """,
            (result.language, result.status, result.reason, result.catalog_product_id, row["store_id"], row["variant_id"]),
        )
    connection.commit()
    return len(rows)
