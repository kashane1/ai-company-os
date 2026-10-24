"""Store report: store health, match quality, prices and how long stock lasts.

Prices are classed against MSRP (`msrp.py`, plan phase P3), compared with the
latest reference-catalog market price, and checked against the founder's
`alert_at` for watched items. "Matched" means `exact` or `confirmed` by a
review decision. Nothing here alerts yet (P4).
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import statistics
from dataclasses import dataclass

from .. import watchlist
from ..db import iso
from . import mail, match, msrp, registry


@dataclass(frozen=True)
class Offer:
    store: str
    product: str
    price_cents: int
    market_cents: int | None
    alert_at_cents: int | None
    url: str
    product_id: int | None = None
    trust: str = "unvetted"
    price_class: msrp.PriceClass | None = None

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
        FROM ref_price_points p
        JOIN (SELECT product_id, MAX(day) AS day FROM ref_price_points WHERE market_price IS NOT NULL GROUP BY product_id) latest
          ON latest.product_id = p.product_id AND latest.day = p.day
        """
    ).fetchall()
    return {row["product_id"]: round(row["market_price"] * 100) for row in rows if row["market_price"]}


def offers(
    connection: sqlite3.Connection, thresholds: dict[int, int], resolver: msrp.Resolver | None = None
) -> list[Offer]:
    """In-stock exact matches, cheapest first within each product, with their MSRP class."""
    market = _market_cents(connection)
    resolver = resolver or msrp.Resolver.from_db(connection)
    rows = connection.execute(
        """
        SELECT s.name AS store, s.trust, p.name AS product, p.product_type, p.exclusive_retailer,
               COALESCE(p.release_on, g.published_on) AS release_on, l.catalog_product_id, l.price_cents, l.url
        FROM store_listings l
        JOIN stores s USING (store_id)
        JOIN ref_products p ON p.product_id = l.catalog_product_id
        JOIN ref_groups g ON g.group_id = p.group_id
        WHERE l.match_status IN ('exact', 'confirmed') AND l.is_available = 1 AND l.price_cents IS NOT NULL
        ORDER BY p.name, l.price_cents
        """
    ).fetchall()
    resolved: dict[int, msrp.Msrp | None] = {}
    result = []
    for row in rows:
        product_id = row["catalog_product_id"]
        if product_id not in resolved:
            resolved[product_id] = resolver.resolve(
                msrp.Product(product_id, row["product"], row["product_type"], row["exclusive_retailer"], row["release_on"])
            )
        market_cents = market.get(product_id)
        result.append(
            Offer(
                store=row["store"],
                product=row["product"],
                price_cents=row["price_cents"],
                market_cents=market_cents,
                alert_at_cents=thresholds.get(product_id),
                url=row["url"],
                product_id=product_id,
                trust=row["trust"],
                price_class=msrp.classify(row["price_cents"], resolved[product_id], market_cents),
            )
        )
    return result


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
        JOIN ref_products p ON p.product_id = l.catalog_product_id
        WHERE l.match_status IN ('exact', 'confirmed')
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


def offer_line(offer: Offer) -> str:
    """One offer with its MSRP basis and market, e.g. for the alert-eligible list."""
    price_class = offer.price_class
    reference = price_class.msrp
    text = (
        f"{offer.store} · {offer.trust} · {offer.product} {_money(offer.price_cents)} "
        f"(MSRP {_money(reference.msrp_cents)} {reference.label}, market {_money(offer.market_cents)})"
    )
    if price_class.name == "below_msrp" and offer.trust == "unvetted":
        text += "  ! unvetted store, below MSRP, check before paying"
    return text


def store_health(connection: sqlite3.Connection, stores: list[registry.Store]) -> str:
    """One line for `radar sources`: polled store status and why others aren't polled."""
    rows = {row["store_id"]: row for row in connection.execute("SELECT * FROM stores")}
    counts = {"ok": 0, "failing": 0, "never": 0}
    not_polled: dict[str, int] = {}
    for store in stores:
        reason = store.not_polled_reason
        if reason:
            not_polled[reason] = not_polled.get(reason, 0) + 1
            continue
        row = rows.get(store.store_id)
        if row is None or not row["last_success_at"]:
            counts["never"] += 1
        elif row["consecutive_failures"]:
            counts["failing"] += 1
        else:
            counts["ok"] += 1
    skipped = ", ".join(f"{count} {reason}" for reason, count in sorted(not_polled.items()))
    return (
        f"stores: {counts['ok']} ok, {counts['failing']} failing, {counts['never']} not yet read; "
        f"not polled: {skipped or 'none'}"
    )


def render(connection: sqlite3.Connection, *, now: dt.datetime, days: int = 7, show_unmatched: int = 0) -> str:
    since = now - dt.timedelta(days=days)
    stores = registry.load()
    polled = {store.store_id for store in stores if store.is_polled}
    lines = [f"Independent store report (collection only, no alerts), last {days} days", store_health(connection, stores), ""]

    lines.append(
        f"{'store':<28} {'tier':<10} {'status':<8} {'last ok':<16} {'sweep':<11} {'kept':>6} {'match':>6} "
        f"{'in stock':>8} {'new':>4}  note"
    )
    for row in connection.execute(
        """
        SELECT s.*, c.selected_count, c.error AS collection_error,
          (SELECT COUNT(*) FROM store_listings l WHERE l.store_id = s.store_id) AS listings,
          (SELECT COUNT(*) FROM store_listings l WHERE l.store_id = s.store_id
             AND l.match_status IN ('exact', 'confirmed')) AS exact,
          (SELECT COUNT(*) FROM store_listings l WHERE l.store_id = s.store_id
             AND l.match_status IN ('exact', 'confirmed')
             AND l.is_available = 1) AS in_stock,
          (SELECT COUNT(*) FROM store_listings l WHERE l.store_id = s.store_id AND l.is_baseline = 0
             AND l.first_seen_at >= ?) AS new
        FROM stores s LEFT JOIN store_collection_checks c USING (store_id)
        ORDER BY s.tier, s.name
        """,
        (iso(since),),
    ):
        if row["store_id"] not in polled:
            continue
        status = "failing" if row["consecutive_failures"] else ("ok" if row["last_success_at"] else "never")
        if row["selected_count"]:
            sweep = f"{row['selected_count']} coll."
        elif row["last_full_sweep_at"]:
            sweep = "catalog"
        else:
            sweep = "pending"
        note = (row["last_error"] or "")[:60]
        if not note and row["is_last_sweep_truncated"]:
            note = f"sweep stopped at {row['last_sweep_pages']} pages"
        last_ok = (row["last_success_at"] or "-")[:16]
        lines.append(
            f"{row['name'][:28]:<28} {row['tier']:<10} {status:<8} {last_ok:<16} {sweep:<11} {row['listings']:>6} "
            f"{row['exact']:>6} {row['in_stock']:>8} {row['new']:>4}  {note}"
        )

    unpolled = [store for store in stores if not store.is_polled]
    if unpolled:
        lines += ["", f"Not polled ({len(unpolled)}):"]
        for store in sorted(unpolled, key=lambda s: (s.not_polled_reason or "", s.name.lower())):
            newsletter = "  newsletter signup" if store.has_newsletter else ""
            lines.append(f"  {store.name[:32]:<32} {store.domain[:32]:<32} {store.not_polled_reason}{newsletter}")

    lines += ["", "Match quality (kept Pokémon listings; singles, graded, non-English and similar are not kept):"]
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
    lines += ["", f"In-stock matched offers: {len(current)} across {len({o.product for o in current})} products."]
    lines.append(f"At or below your watchlist alert_at: {len(under)}")
    for offer in under:
        lines.append(f"  {_money(offer.price_cents):>9}  {offer.product}  @ {offer.store}  (alert_at {_money(offer.alert_at_cents)})")

    lines += ["", "MSRP classes of in-stock offers (estimated MSRPs rank but never alert):"]
    class_counts: dict[str, list[int]] = {}
    for offer in current:
        price_class = offer.price_class
        counts = class_counts.setdefault(price_class.name, [0, 0])
        counts[0 if price_class.msrp is None or not price_class.msrp.is_estimated else 1] += 1
    for name in msrp.CLASS_ORDER:
        if name in class_counts:
            evidence, estimated = class_counts[name]
            lines.append(f"  {name:<11} {evidence + estimated:>6}  ({estimated} on an estimated MSRP)")

    eligible = [offer for offer in current if offer.price_class.is_alert_eligible]
    lines += ["", f"At or below MSRP with evidence (alert-eligible from P4): {len(eligible)}"]
    for offer in sorted(eligible, key=lambda o: o.price_class.ratio):
        lines.append("  " + offer_line(offer))

    lines += ["", "Cheapest in-stock offer per product vs MSRP and tcgcsv market:"]
    cheapest: dict[str, Offer] = {}
    for offer in current:
        cheapest.setdefault(offer.product, offer)
    for product, offer in sorted(cheapest.items()):
        ratio = offer.market_ratio
        ratio_text = f"{ratio:.2f}x" if ratio is not None else "-"
        price_class = offer.price_class
        msrp_text = (
            f"{price_class.name:<10} MSRP {_money(price_class.msrp.msrp_cents):>8} {price_class.msrp.label:<10}"
            if price_class.msrp else f"{'no_msrp':<10} {'':<24}"
        )
        lines.append(
            f"  {_money(offer.price_cents):>9}  {msrp_text}  {ratio_text:>6} market {_money(offer.market_cents):>9}  "
            f"{product[:60]}  @ {offer.store}"
        )

    spans = in_stock_spans(connection, since)
    lines += ["", f"Exact-match stock that sold out in the window: {len(spans)}"]
    if spans:
        minutes = [span[2] for span in spans]
        lines.append(f"  median in stock {statistics.median(minutes):.0f} min, shortest {min(minutes):.0f} min")
        for store, product, span_minutes in sorted(spans, key=lambda span: span[2])[:15]:
            lines.append(f"  {span_minutes:>7.0f} min  {product[:60]}  @ {store}")

    emails = mail.summary(connection, since=since)
    subscribed = [store for store in stores if store.email_status == "subscribed"]
    founder = [store for store in stores if store.email_status == "needs_founder"]
    lines += ["", f"Store emails: subscribed at {len(subscribed)} stores, {len(founder)} need the founder's signup (CAPTCHA)."]
    lines += emails or ["  none received yet (needs the Gmail forwarding filter: radar store-mail-filter)"]

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
