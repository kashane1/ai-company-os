"""Store alerts (plan phase P4): MSRP hits on independent stores become alerts.

After each store read, every listing that changed in a way that can make it
newly buyable is checked: it appeared (outside a store's baseline sweep),
came back in stock, or dropped in price while in stock. Each such in-stock,
English, matched listing becomes an observation (source `stores`, author
the store id), so episodes and the scorecard treat stores like any other
source.

It alerts when its MSRP class is `at_msrp` or `below_msrp` on an
evidence-backed MSRP and either:

- its product is watched: the price must also be at or below the watch's
  `alert_at` (so `min(alert_at, 1.10 × MSRP)`); or
- its set is watched: any English sealed product of a watched set at or
  below MSRP (founder decision 2026-10-23).

A watched product whose MSRP has no evidence alerts at or below `alert_at`.
`[exclude] terms` always win, `marked_up` never alerts, and below-MSRP offers
or far below market on unvetted stores carry a warning. One notification per episode, only while
the change is fresh. Store links are never opened automatically: assisted
open needs a store with `trust = purchased_ok`, and none has one yet.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Callable

from .. import episodes, watchlist
from ..catalog.classify import set_key
from ..db import iso
from ..matching import normalize
from ..notify import MAX_AGE, Sender, macos_notify
from . import match, msrp, report

SOURCE_ID = "stores"
_PREORDER = re.compile(r"\bpre[- ]?orders?\b|\bpresale\b", re.IGNORECASE)
CLASS_LABELS = {"below_msrp": "Below MSRP", "at_msrp": "At MSRP"}


@dataclass(frozen=True)
class Candidate:
    store_id: str
    store: str
    trust: str
    variant_id: int
    observed_at: str
    change: str
    title: str
    url: str
    price_cents: int
    product_id: int
    product: str
    group_name: str
    price_class: msrp.PriceClass
    market_cents: int | None


@dataclass(frozen=True)
class Decision:
    should_alert: bool
    reason: str
    watch_name: str | None = None


@dataclass(frozen=True)
class WatchContext:
    """What the watchlist says about products and sets."""

    thresholds: dict[int, int]  # catalog product id -> lowest alert_at in cents
    watch_names: dict[int, list[str]]  # catalog product id -> watch item names
    set_keys: frozenset[str]
    exclude_terms: tuple[str, ...]


def watch_context(connection: sqlite3.Connection, catalog: match.Catalog, policy: watchlist.Policy) -> WatchContext:
    items = [
        item for item in policy.items
        if getattr(item, "identity", None) is None
        or (item.identity.language == "en" and item.identity.game == "pokemon")
    ]
    watch_names: dict[int, list[str]] = {}
    watched_groups: set[int] = set()
    unmatched: list[str] = []
    for item in items:
        result = match.match_listing(catalog, item.name)
        if result.status == "exact" and result.catalog_product_id is not None:
            watch_names.setdefault(result.catalog_product_id, []).append(item.name)
            row = connection.execute(
                "SELECT group_id FROM ref_products WHERE product_id = ?", (result.catalog_product_id,)
            ).fetchone()
            if row:
                watched_groups.add(row["group_id"])
        else:
            unmatched.append(item.name)
    group_names = {row["group_id"]: row["name"] for row in connection.execute("SELECT group_id, name FROM ref_groups")}
    keys = {set_key(group_names[group_id]) for group_id in watched_groups if group_id in group_names}
    # Names the matcher can't pin to one product still name their set.
    keys |= _set_keys_named(group_names.values(), unmatched)
    return WatchContext(
        thresholds=report.watch_thresholds(catalog, items),
        watch_names=watch_names,
        set_keys=frozenset(keys),
        exclude_terms=policy.exclude_terms,
    )


# Era names that also prefix product names of later sets in the era.
_ERA_KEYS = frozenset({"mega evolution", "scarlet & violet", "sword & shield", "sun & moon"})


def _set_keys_named(group_names, item_names: list[str]) -> set[str]:
    """Set keys named inside item names. "Mega Evolution Delta Reign ETB" names Delta Reign, not the era."""
    all_keys = {key for key in (set_key(name) for name in group_names) if len(key) >= watchlist.MIN_SET_KEY_LENGTH}
    keys: set[str] = set()
    for item in item_names:
        lowered = item.lower()
        found = {key for key in all_keys if key in lowered}
        found = {key for key in found if not any(key != other and key in other for other in found)}
        if len(found) > 1:
            found -= _ERA_KEYS
        keys |= found
    return keys


def decide(candidate: Candidate, context: WatchContext) -> Decision:
    text = normalize(f"{candidate.product} {candidate.title}")
    if any(normalize(term) in text for term in context.exclude_terms):
        return Decision(False, "excluded term")
    price_class = candidate.price_class
    names = context.watch_names.get(candidate.product_id) or []
    watch_name = names[0] if names else None
    limit = context.thresholds.get(candidate.product_id)
    if limit is not None:
        if candidate.price_cents > limit:
            return Decision(False, "watched, above alert_at", watch_name)
        if price_class.msrp is None or price_class.msrp.is_estimated:
            return Decision(True, "watched, at or below alert_at", watch_name)
        if price_class.is_alert_eligible:
            return Decision(True, f"watched, {price_class.name}", watch_name)
        return Decision(False, f"watched, {price_class.name}", watch_name)
    if not price_class.is_alert_eligible:
        return Decision(False, price_class.name if price_class.msrp else "no evidence MSRP")
    if set_key(candidate.group_name) in context.set_keys:
        return Decision(True, f"watched set, {price_class.name}")
    return Decision(False, "set not watched")


def candidates(
    connection: sqlite3.Connection, *, now: dt.datetime, resolver: msrp.Resolver
) -> list[Candidate]:
    """Fresh changes that leave a matched English listing in stock and no more expensive than before."""
    since = iso(now - MAX_AGE)
    market = report._market_cents(connection)
    rows = connection.execute(
        """
        SELECT n.store_id, n.variant_id, n.observed_at, n.change, n.price_cents,
               s.name AS store, s.trust, l.title, l.url, l.is_baseline, l.catalog_product_id,
               p.name AS product, p.product_type, p.exclusive_retailer,
               COALESCE(p.release_on, g.published_on) AS release_on, g.name AS group_name,
               (SELECT prev.price_cents FROM listing_snapshots prev
                 WHERE prev.store_id = n.store_id AND prev.variant_id = n.variant_id
                   AND prev.observed_at < n.observed_at
                 ORDER BY prev.observed_at DESC LIMIT 1) AS previous_price,
               (SELECT prev.is_available FROM listing_snapshots prev
                 WHERE prev.store_id = n.store_id AND prev.variant_id = n.variant_id
                   AND prev.observed_at < n.observed_at
                 ORDER BY prev.observed_at DESC LIMIT 1) AS previous_available
        FROM listing_snapshots n
        JOIN store_listings l ON l.store_id = n.store_id AND l.variant_id = n.variant_id
        JOIN stores s ON s.store_id = n.store_id
        JOIN ref_products p ON p.product_id = l.catalog_product_id
        JOIN ref_groups g ON g.group_id = p.group_id
        WHERE n.observed_at >= ? AND n.is_available = 1 AND n.price_cents IS NOT NULL AND s.trust != 'avoid' 
          AND l.match_status IN ('exact', 'confirmed') AND l.language = 'en'
        ORDER BY n.observed_at, n.store_id, n.variant_id
        """,
        (since,),
    ).fetchall()
    result = []
    for row in rows:
        if row["change"] == "first_seen" and row["is_baseline"]:
            continue  # a store's first sweep isn't news
        is_restock = row["previous_available"] == 0
        is_cheaper = row["previous_price"] is not None and row["price_cents"] < row["previous_price"]
        if row["change"] != "first_seen" and not (is_restock or is_cheaper):
            continue  # price went up, or nothing that makes it newly buyable
        product = msrp.Product(row["catalog_product_id"], row["product"], row["product_type"],
                               row["exclusive_retailer"], row["release_on"])
        market_cents = market.get(row["catalog_product_id"])
        result.append(
            Candidate(
                store_id=row["store_id"], store=row["store"], trust=row["trust"], variant_id=row["variant_id"],
                observed_at=row["observed_at"], change=row["change"], title=row["title"], url=row["url"],
                price_cents=row["price_cents"], product_id=row["catalog_product_id"], product=row["product"],
                group_name=row["group_name"],
                price_class=msrp.classify(row["price_cents"], resolver.resolve(product), market_cents),
                market_cents=market_cents,
            )
        )
    return result


def _money(cents: int | None) -> str:
    return "-" if cents is None else f"${cents / 100:,.2f}"


def message(candidate: Candidate, decision: Decision) -> tuple[str, str]:
    price_class = candidate.price_class
    label = CLASS_LABELS.get(price_class.name, "Under your alert_at")
    caution = msrp.warning(price_class, candidate.trust, candidate.price_cents, candidate.market_cents)
    title = f"{label}{' (unvetted store)' if caution else ''} · {candidate.store}"
    reference = price_class.msrp
    msrp_text = f"MSRP {_money(reference.msrp_cents)} {reference.label}" if reference else "no MSRP"
    lines = [
        f"{candidate.product} {_money(candidate.price_cents)} ({msrp_text}, market {_money(candidate.market_cents)})",
        f"{candidate.store} · {candidate.trust} · {decision.reason}",
    ]
    if caution:
        lines.append(caution)
    lines.append(candidate.url)
    return title, "\n".join(lines)


def _record_observation(connection: sqlite3.Connection, candidate: Candidate, decision: Decision) -> int | None:
    signal = "preorder" if _PREORDER.search(candidate.title) else "in_stock"
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO observations
            (source_id, external_id, author, text, signal, retailer, product_text, price, url, is_tcg,
             watch_matches, source_time, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            SOURCE_ID,
            f"{candidate.store_id}:{candidate.variant_id}:{candidate.observed_at}",
            candidate.store_id,
            candidate.title,
            signal,
            candidate.store,
            candidate.product,
            candidate.price_cents / 100,
            candidate.url,
            json.dumps([decision.watch_name] if decision.watch_name else []),
            candidate.observed_at,
            candidate.observed_at,
        ),
    )
    return cursor.lastrowid if cursor.rowcount else None


def _notify(connection: sqlite3.Connection, episode_id: int, title: str, body: str, *, now: dt.datetime,
            send: Sender) -> bool:
    key = f"episode:{episode_id}"
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO notifications (dedupe_key, episode_id, channel, title, body, created_at, status)
        VALUES (?, ?, 'macos', ?, ?, ?, 'sent')
        """,
        (key, episode_id, title, body, iso(now)),
    )
    connection.commit()
    if not cursor.rowcount:
        return False
    try:
        send(title, body)
    except Exception as exc:  # a failed banner must not break collection
        connection.execute(
            "UPDATE notifications SET status = 'failed', error = ? WHERE dedupe_key = ?",
            (f"{type(exc).__name__}: {exc}"[:300], key),
        )
        connection.commit()
        return False
    return True


@dataclass
class AlertSummary:
    observations: int = 0
    alerts: int = 0


def evaluate(
    connection: sqlite3.Connection,
    *,
    now: dt.datetime,
    send: Sender = macos_notify,
    policy: watchlist.Policy | None = None,
    resolver: msrp.Resolver | None = None,
    catalog: match.Catalog | None = None,
    on_alert: Callable[[str, str], None] | None = None,
) -> AlertSummary:
    """Turn fresh store changes into observations and alert on MSRP hits."""
    catalog = catalog or match.Catalog.from_db(connection)
    resolver = resolver or msrp.Resolver.from_db(connection)
    context = watch_context(connection, catalog, policy or watchlist.load_policy())
    summary = AlertSummary()
    for candidate in candidates(connection, now=now, resolver=resolver):
        decision = decide(candidate, context)
        observation_id = _record_observation(connection, candidate, decision)
        if observation_id is None:
            continue  # already handled on an earlier run
        summary.observations += 1
        episode_ids = episodes.assign(connection, observation_id)
        if not decision.should_alert:
            continue
        title, body = message(candidate, decision)
        for episode_id in episode_ids:
            if _notify(connection, episode_id, title, body, now=now, send=send):
                summary.alerts += 1
                if on_alert:
                    on_alert(title, body)
    connection.commit()
    return summary
