"""Finding a card in the catalog, and deciding what its price actually means.

Reads the attached, read-only `catalog` database built by pokemon-tcg-search.

Two things to understand about the prices in there.

First, they carry no condition dimension. TCGCSV publishes one market price per
*finish* (Normal, Holofoil, Reverse Holofoil), not per condition, so an LP
price is derived by haircutting the NM price with the multipliers in
`conditions`. Those start as market convention and should be re-fit from real
sales.

Second, a quoted price is not always a real one. TCGplayer pins market price
when nothing sells, so a vintage single can report the same number every day
for months without a single transaction and then step down hard when one
finally lands. pokemon-tcg-search already computes the signals that catch this;
`price_health` reads them so an intake or repricing decision can refuse to
trust a stale or artifactual quote instead of acting on it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

# A quote that hasn't moved in this long is a pinned price, not a market.
STALE_AFTER_DAYS = 45

# Below this many distinct prices in 90 days, treat the market as illiquid.
MIN_DISTINCT_PRICES_90D = 4

# A current price this far below the 90-day median is more likely a feed
# artifact than a crash — a real decline drags the median with it.
ARTIFACT_DISCOUNT_PCT = 60.0


@dataclass(frozen=True)
class PriceHealth:
    is_trustworthy: bool
    warnings: tuple[str, ...]

    days_since_price_change: int | None
    distinct_prices_90d: int
    current_vs_median_90d_pct: float | None
    observation_count_30d: int


def search(
    conn: sqlite3.Connection,
    name: str,
    *,
    set_name: str | None = None,
    number: str | None = None,
    limit: int = 20,
) -> list[sqlite3.Row]:
    """Find candidate variants by card name, optionally narrowed by set/number.

    Returns one row per *variant* (finish), not per card, because the finish is
    part of the SKU and is where identification most often goes wrong: holo,
    reverse holo and non-holo of the same card can differ by 50x.
    """
    sql = """
        SELECT variant_id, product_id, card_name, card_number, rarity,
               sub_type, set_name, set_abbreviation, released_on,
               current_price, image_url, tcgplayer_url
          FROM catalog.screener_rows
         WHERE card_name LIKE ?
    """
    params: list[object] = [f"%{name}%"]

    if set_name:
        sql += " AND set_name LIKE ?"
        params.append(f"%{set_name}%")
    if number:
        sql += " AND card_number LIKE ?"
        params.append(f"%{number}%")

    sql += " ORDER BY current_price DESC LIMIT ?"
    params.append(limit)

    return conn.execute(sql, params).fetchall()


def get_variant(conn: sqlite3.Connection, variant_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM catalog.screener_rows WHERE variant_id = ?", (variant_id,)
    ).fetchone()


def market_price_cents(
    conn: sqlite3.Connection, variant_id: int, condition_code: str = "NM"
) -> int | None:
    """NM market price haircut to the given condition, in cents."""
    row = conn.execute(
        "SELECT current_price FROM catalog.card_metrics WHERE variant_id = ?",
        (variant_id,),
    ).fetchone()
    if row is None or row["current_price"] is None:
        return None

    multiplier = conn.execute(
        "SELECT nm_multiplier FROM conditions WHERE condition_code = ?",
        (condition_code,),
    ).fetchone()
    if multiplier is None:
        raise KeyError(f"Unknown condition: {condition_code}")

    return round(row["current_price"] * 100 * multiplier["nm_multiplier"])


def price_health(conn: sqlite3.Connection, variant_id: int) -> PriceHealth:
    """Whether this variant's quoted price can be acted on.

    Every signal here is already computed by pokemon-tcg-search's metrics pass;
    this only applies thresholds to them.
    """
    row = conn.execute(
        """
        SELECT days_since_price_change, distinct_prices_90d,
               current_vs_median_90d_pct, observation_count_30d,
               peak_is_first_observation, peak_within_30d_of_release
          FROM catalog.card_metrics
         WHERE variant_id = ?
        """,
        (variant_id,),
    ).fetchone()

    if row is None:
        return PriceHealth(
            is_trustworthy=False,
            warnings=("no metrics for this variant",),
            days_since_price_change=None,
            distinct_prices_90d=0,
            current_vs_median_90d_pct=None,
            observation_count_30d=0,
        )

    warnings: list[str] = []

    stale_days = row["days_since_price_change"]
    if stale_days is not None and stale_days >= STALE_AFTER_DAYS:
        warnings.append(f"price hasn't moved in {stale_days} days — likely a pinned quote")

    if row["distinct_prices_90d"] < MIN_DISTINCT_PRICES_90D:
        warnings.append(
            f"only {row['distinct_prices_90d']} distinct prices in 90 days — illiquid"
        )

    vs_median = row["current_vs_median_90d_pct"]
    if vs_median is not None and vs_median <= -ARTIFACT_DISCOUNT_PCT:
        warnings.append(
            f"current price is {abs(vs_median):.0f}% below its 90-day median — "
            "probably a feed artifact, not a crash"
        )

    if row["observation_count_30d"] < 10:
        warnings.append(
            f"only {row['observation_count_30d']} observations in the last 30 days"
        )

    return PriceHealth(
        is_trustworthy=not warnings,
        warnings=tuple(warnings),
        days_since_price_change=stale_days,
        distinct_prices_90d=row["distinct_prices_90d"],
        current_vs_median_90d_pct=vs_median,
        observation_count_30d=row["observation_count_30d"],
    )
