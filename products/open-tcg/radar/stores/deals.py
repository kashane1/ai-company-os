"""Daily deals digest (`radar deals`, plan phase P4).

The cheapest in-stock English sealed offer per catalog product across all
polled stores, grouped by MSRP class, with the change since a day earlier.
`marked_up` offers are counted but never listed.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

from ..db import iso
from . import msrp, report

LISTED_CLASSES = ("below_msrp", "at_msrp", "near_msrp", "market")


@dataclass(frozen=True)
class Deal:
    offer: report.Offer
    yesterday_cents: int | None  # cheapest in-stock price for the product a day earlier


def _cheapest_at(connection: sqlite3.Connection, moment: dt.datetime) -> dict[int, int]:
    """Catalog product id -> cheapest in-stock price at `moment`, from listing snapshots."""
    rows = connection.execute(
        """
        SELECT l.catalog_product_id, MIN(n.price_cents) AS price_cents
        FROM listing_snapshots n
        JOIN store_listings l ON l.store_id = n.store_id AND l.variant_id = n.variant_id
        WHERE l.match_status IN ('exact', 'confirmed') AND l.language = 'en'
          AND n.observed_at = (
            SELECT MAX(m.observed_at) FROM listing_snapshots m
            WHERE m.store_id = n.store_id AND m.variant_id = n.variant_id AND m.observed_at <= ?)
          AND n.is_available = 1 AND n.price_cents IS NOT NULL
        GROUP BY l.catalog_product_id
        """,
        (iso(moment),),
    ).fetchall()
    return {row["catalog_product_id"]: row["price_cents"] for row in rows}


def deals(connection: sqlite3.Connection, *, now: dt.datetime, resolver: msrp.Resolver | None = None) -> list[Deal]:
    current = report.offers(connection, {}, resolver)
    yesterday = _cheapest_at(connection, now - dt.timedelta(days=1))
    cheapest: dict[int, report.Offer] = {}
    for offer in current:  # cheapest first within each product
        cheapest.setdefault(offer.product_id, offer)
    return [Deal(offer, yesterday.get(product_id)) for product_id, offer in cheapest.items()]


def _money(cents: int | None) -> str:
    return "-" if cents is None else f"${cents / 100:,.2f}"


def _change(deal: Deal) -> str:
    if deal.yesterday_cents is None:
        return "new"
    delta = deal.offer.price_cents - deal.yesterday_cents
    return "same" if delta == 0 else f"{'+' if delta > 0 else '-'}{_money(abs(delta))}"


def render(connection: sqlite3.Connection, *, now: dt.datetime, limit: int = 40) -> str:
    items = deals(connection, now=now)
    by_class: dict[str, list[Deal]] = {}
    for deal in items:
        by_class.setdefault(deal.offer.price_class.name, []).append(deal)
    lines = [f"Store deals digest, {now.astimezone().strftime('%Y-%m-%d %H:%M')}: cheapest in-stock offer per product"]
    for name in LISTED_CLASSES:
        group = sorted(by_class.get(name, []), key=lambda d: (d.offer.price_class.ratio or 0, d.offer.product))
        if not group:
            continue
        lines += ["", f"{name} ({len(group)})"]
        for deal in group[:limit]:
            offer = deal.offer
            reference = offer.price_class.msrp
            caution = msrp.warning(offer.price_class, offer.trust, offer.price_cents, offer.market_cents)
            warning = "  ! unvetted, check first" if caution else ""
            lines.append(
                f"  {_money(offer.price_cents):>9}  MSRP {_money(reference.msrp_cents):>8} {reference.label:<10} "
                f"market {_money(offer.market_cents):>9}  {_change(deal):>8}  {offer.product[:55]}  @ {offer.store}{warning}"
            )
        if len(group) > limit:
            lines.append(f"  … {len(group) - limit} more")
    hidden = {name: len(by_class.get(name, [])) for name in ("marked_up", "no_msrp")}
    lines += ["", f"Not listed: {hidden['marked_up']} marked up, {hidden['no_msrp']} with no MSRP (radar msrp missing)."]
    return "\n".join(lines) + "\n"
