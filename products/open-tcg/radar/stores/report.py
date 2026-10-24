"""Pilot report: store health, match quality, prices and how long stock lasts.

There is no MSRP table yet (plan phase P3), so prices are compared with the
latest tcgcsv market price and with the founder's `alert_at` for watched items.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import statistics
from dataclasses import dataclass

from .. import watchlist
from ..db import iso
from . import match


@dataclass(frozen=True)
class Offer:
    store: str
    product: str
    price_cents: int
    market_cents: int | None
    alert_at_cents: int | None
    url: str

    @property
    def market_ratio(self) -> float | None:
        if not self.market_cents:
            return None
        return self.price_cents / self.market_cents

    @property
    def is_at_or_below_alert_at(self) -> bool:
        return self.alert_at_cents is not None and self.price_cents <= self.alert_at_cents


def watch_thresholds(catalog: match.Catalog, items: list[watchlist.WatchItem]) -> dict[int, int]:
    """Catalog product id -> lowest `alert_at` (cents) of the English watches naming it."""
    thresholds: dict[int, int] = {}
    for item in items:
        if item.alert_at is None:
            continue
        # Legacy watches carry no identity; they are English Pokémon items.
        identity = getattr(item, "identity", None)
        if identity is not None and (identity.language != "en" or identity.game != "pokemon"):
            continue
        result = match.match_listing(catalog, item.name)
        if result.status != "exact" or result.catalog_product_id is None:
            continue
        cents = round(item.alert_at * 100)
        previous = thresholds.get(result.catalog_product_id)
        thresholds[result.catalog_product_id] = cents if previous is None else min(previous, cents)
    return thresholds


def _market_cents(connection: sqlite3.Connection) -> dict[int, int]:
    rows = connection.execute(
        """
        SELECT p.product_id, p.market_price
        FROM price_points p
        JOIN (SELECT product_id, MAX(day) AS day FROM price_points WHERE market_price IS NOT NULL GROUP BY product_id) latest
          ON latest.product_id = p.product_id AND latest.day = p.day
        """
    ).fetchall()
    return {row["product_id"]: round(row["market_price"] * 100) for row in rows if row["market_price"]}


def offers(connection: sqlite3.Connection, thresholds: dict[int, int]) -> list[Offer]:
    """In-stock exact matches, cheapest first within each product."""
    market = _market_cents(connection)
    rows = connection.execute(
        """
        SELECT s.name AS store, p.name AS product, l.catalog_product_id, l.price_cents, l.url
        FROM store_listings l
        JOIN stores s USING (store_id)
        JOIN products p ON p.product_id = l.catalog_product_id
        WHERE l.match_status = 'exact' AND l.is_available = 1 AND l.price_cents IS NOT NULL
        ORDER BY p.name, l.price_cents
        """
    ).fetchall()
    return [
        Offer(
            store=row["store"],
            product=row["product"],
            price_cents=row["price_cents"],
            market_cents=market.get(row["catalog_product_id"]),
            alert_at_cents=thresholds.get(row["catalog_product_id"]),
            url=row["url"],
        )
        for row in rows
    ]


def in_stock_spans(connection: sqlite3.Connection, since: dt.datetime) -> list[tuple[str, str, float]]:
    """(store, product, minutes) for exact-match stock that went out of stock since `since`.

    Durations are only as fine as polling: a listing seen only by the daily
    sweep can be off by up to a day.
    """
    rows = connection.execute(
        """
        SELECT s.name AS store, p.name AS product, n.store_id, n.variant_id, n.observed_at, n.is_available,
               n.change, l.is_baseline
        FROM listing_snapshots n
        JOIN store_listings l USING (store_id, variant_id)
        JOIN stores s USING (store_id)
        JOIN products p ON p.product_id = l.catalog_product_id
        WHERE l.match_status = 'exact'
        ORDER BY n.store_id, n.variant_id, n.observed_at
        """
    ).fetchall()
    spans = []
    started: dict[tuple[str, int], str] = {}
    for row in rows:
        key = (row["store_id"], row["variant_id"])
        # A baseline listing's first sighting isn't when its stock arrived.
        if row["change"] == "first_seen" and row["is_baseline"]:
            continue
        if row["is_available"]:
            started.setdefault(key, row["observed_at"])
        elif key in started:
            start = started.pop(key)
            if row["observed_at"] >= iso(since):
                minutes = (dt.datetime.fromisoformat(row["observed_at"]) - dt.datetime.fromisoformat(start)).total_seconds() / 60
                spans.append((row["store"], row["product"], minutes))
    return spans


def _money(cents: int | None) -> str:
    return "-" if cents is None else f"${cents / 100:,.2f}"


def render(connection: sqlite3.Connection, *, now: dt.datetime, days: int = 7, show_unmatched: int = 0) -> str:
    since = now - dt.timedelta(days=days)
    lines = [f"Store pilot report (collection only, no alerts), last {days} days", ""]

    lines.append(f"{'store':<28} {'status':<8} {'last ok':<16} {'pokemon':>7} {'exact':>6} {'in stock':>8} {'new':>4}  note")
    for row in connection.execute(
        """
        SELECT s.*,
          (SELECT COUNT(*) FROM store_listings l WHERE l.store_id = s.store_id) AS listings,
          (SELECT COUNT(*) FROM store_listings l WHERE l.store_id = s.store_id AND l.match_status = 'exact') AS exact,
          (SELECT COUNT(*) FROM store_listings l WHERE l.store_id = s.store_id AND l.match_status = 'exact'
             AND l.is_available = 1) AS in_stock,
          (SELECT COUNT(*) FROM store_listings l WHERE l.store_id = s.store_id AND l.is_baseline = 0
             AND l.first_seen_at >= ?) AS new
        FROM stores s ORDER BY s.name
        """,
        (iso(since),),
    ):
        status = "failing" if row["consecutive_failures"] else ("ok" if row["last_success_at"] else "never")
        note = (row["last_error"] or "")[:60]
        if not note and row["is_last_sweep_truncated"]:
            note = f"sweep stopped at {row['last_sweep_pages']} pages"
        last_ok = (row["last_success_at"] or "-")[:16]
        lines.append(
            f"{row['name'][:28]:<28} {status:<8} {last_ok:<16} {row['listings']:>7} {row['exact']:>6} "
            f"{row['in_stock']:>8} {row['new']:>4}  {note}"
        )

    lines += ["", "Match quality (all Pokémon listings):"]
    for row in connection.execute(
        """
        SELECT match_status, COALESCE(match_reason, '') AS reason, COUNT(*) AS n
        FROM store_listings GROUP BY 1, 2 ORDER BY n DESC
        """
    ):
        lines.append(f"  {row['n']:>6}  {row['match_status']:<10} {row['reason']}")

    catalog = match.Catalog.from_db(connection)
    thresholds = watch_thresholds(catalog, watchlist.load())
    current = offers(connection, thresholds)
    under = [offer for offer in current if offer.is_at_or_below_alert_at]
    lines += ["", f"In-stock exact offers: {len(current)} across {len({o.product for o in current})} products."]
    lines.append(f"At or below your watchlist alert_at: {len(under)}")
    for offer in under:
        lines.append(f"  {_money(offer.price_cents):>9}  {offer.product}  @ {offer.store}  (alert_at {_money(offer.alert_at_cents)})")

    lines += ["", "Cheapest in-stock offer per product vs tcgcsv market:"]
    cheapest: dict[str, Offer] = {}
    for offer in current:
        cheapest.setdefault(offer.product, offer)
    for product, offer in sorted(cheapest.items()):
        ratio = offer.market_ratio
        ratio_text = f"{ratio:.2f}x" if ratio is not None else "-"
        lines.append(
            f"  {_money(offer.price_cents):>9}  {ratio_text:>6} market {_money(offer.market_cents):>9}  {product[:60]}  @ {offer.store}"
        )

    spans = in_stock_spans(connection, since)
    lines += ["", f"Exact-match stock that sold out in the window: {len(spans)}"]
    if spans:
        minutes = [span[2] for span in spans]
        lines.append(f"  median in stock {statistics.median(minutes):.0f} min, shortest {min(minutes):.0f} min")
        for store, product, span_minutes in sorted(spans, key=lambda span: span[2])[:15]:
            lines.append(f"  {span_minutes:>7.0f} min  {product[:60]}  @ {store}")

    if show_unmatched:
        lines += ["", f"Sample of English listings not matched exactly (up to {show_unmatched}):"]
        for row in connection.execute(
            """
            SELECT match_status, match_reason, title FROM store_listings
            WHERE language = 'en' AND match_status IN ('ambiguous', 'unmatched')
            ORDER BY last_seen_at DESC LIMIT ?
            """,
            (show_unmatched,),
        ):
            lines.append(f"  {row['match_status']:<9} {row['match_reason'] or '':<18} {row['title'][:80]}")
    return "\n".join(lines) + "\n"
