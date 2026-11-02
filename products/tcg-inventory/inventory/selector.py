"""Which cards to list, given that you cannot list them all.

At TCGplayer Level 1 you get 100 listings and $1,000 of listed value. With 500
sellable cards that is the binding constraint on the whole operation — not
syncing, not pricing. Choosing the wrong 100 costs more than any other decision
the software makes.

What to optimize for is not profit. Level 4 — which unlocks CSV import/export
and with it every piece of real automation — is gated on 51 delivered orders,
not on dollars. So early on an order is worth more than a margin, and the
objective here is expected orders per week subject to the caps.

## Estimating velocity

TCGCSV carries no sales counts, so sell-through has to be inferred. Of the four
candidate signals in card_metrics, measured against the real catalog for cards
between $0.50 and $50, only two survive:

  distinct_prices_90d     USED. Range 1-63, median 10, top decile 37+. The best
                          available liquidity proxy: a price that moves is a
                          price someone is trading at.
  days_since_price_change USED, but weakly. 77% of a realistic pool changed
                          within the last week, so this discriminates only at
                          the stale tail. Weighted accordingly.

  coverage_30d_pct        REJECTED. Averages 99 across the catalog and is 100
                          for almost everything, because TCGplayer reports a
                          price every day whether or not anything sold. It
                          cannot distinguish a live market from a frozen one.
  spread_pct              REJECTED. Averages 8,344 and tops out near 20,000,000
                          — corrupted by near-zero lows. Unusable without
                          clamping so aggressive that nothing is left.

This is a proxy, not a measurement, and it should be replaced by your own
sell-through data once there is enough of it. Until then it is a ranking
heuristic and should not be read as a probability.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from . import catalog, economics as ec

MOVEMENT_WEIGHT = 0.7
FRESHNESS_WEIGHT = 0.3


@dataclass(frozen=True)
class Candidate:
    copy_id: int
    variant_id: int
    card_name: str
    sub_type: str
    condition_code: str
    set_name: str
    price_cents: int
    velocity: float

    @property
    def expected_value_cents(self) -> float:
        """Rough expected weekly contribution. Used only for reporting."""
        return self.price_cents * self.velocity


@dataclass(frozen=True)
class Rejection:
    candidate: Candidate
    reason: str


@dataclass
class ListingPlan:
    channel: str
    selected: list[Candidate]
    rejected: list[Rejection]
    listing_cap: int | None
    value_cap_cents: int | None

    @property
    def listing_count(self) -> int:
        return len(self.selected)

    @property
    def value_cents(self) -> int:
        return sum(c.price_cents for c in self.selected)

    @property
    def expected_orders_index(self) -> float:
        """Sum of velocity scores. Comparable between plans, not a real count."""
        return sum(c.velocity for c in self.selected)


def _percentile_ranks(values: list[float]) -> list[float]:
    """Rank each value in 0..1 against the others. Ties share the mean rank."""
    count = len(values)
    if count == 0:
        return []
    if count == 1:
        return [1.0]

    order = sorted(range(count), key=lambda i: values[i])
    ranks = [0.0] * count
    position = 0
    while position < count:
        end = position
        while end + 1 < count and values[order[end + 1]] == values[order[position]]:
            end += 1
        shared = (position + end) / 2 / (count - 1)
        for index in range(position, end + 1):
            ranks[order[index]] = shared
        position = end + 1
    return ranks


def velocity_scores(
    movement: list[int | None], staleness: list[int | None]
) -> list[float]:
    """Rank a pool of cards by how likely each is to sell, relative to the rest.

    Scoring is pool-relative on purpose. An absolute formula looked fine and was
    useless in practice: 77% of a realistic 500-card pool has a price change
    within the last week, so any freshness curve saturates for three cards in
    four, and the whole ranking collapses to "cheapest first". Percentile rank
    spreads the pool across 0..1 whatever the absolute distribution happens to
    be.

    The consequence to keep in mind is that a card's score depends on what else
    you own. For choosing among the cards you have, that is the correct
    behavior — but it means a score is not comparable between runs, and it is
    emphatically not a probability of selling.
    """
    # A missing or never-changing price ranks as maximally stale.
    staleness_values = [float(s) if s is not None else float("inf") for s in staleness]
    movement_values = [float(m or 0) for m in movement]

    movement_rank = _percentile_ranks(movement_values)
    # Negated: fewer days since the last change should rank higher.
    freshness_rank = _percentile_ranks([-s for s in staleness_values])

    return [
        MOVEMENT_WEIGHT * movement_rank[i] + FRESHNESS_WEIGHT * freshness_rank[i]
        for i in range(len(movement_values))
    ]


def candidates(conn: sqlite3.Connection, channel: str) -> list[Candidate]:
    """Every copy that could go on this channel but is not already live there."""
    rows = conn.execute(
        """
        SELECT c.copy_id, c.variant_id, c.condition_code,
               s.card_name, s.sub_type, s.set_name,
               m.distinct_prices_90d, m.days_since_price_change
          FROM copies c
          JOIN catalog.screener_rows s ON s.variant_id = c.variant_id
          LEFT JOIN catalog.card_metrics m ON m.variant_id = c.variant_id
         WHERE NOT EXISTS (
                 SELECT 1 FROM listings l
                  WHERE l.copy_id = c.copy_id
                    AND l.channel = ?
                    AND l.ended_at IS NULL
               )
           AND NOT EXISTS (
                 SELECT 1 FROM copy_current_state cs
                  WHERE cs.copy_id = c.copy_id
                    AND cs.state IN ('sold', 'lost', 'outbound', 'in_transit')
               )
        """,
        (channel,),
    ).fetchall()

    priced = [
        (row, price)
        for row in rows
        if (price := catalog.market_price_cents(
            conn, row["variant_id"], row["condition_code"]
        ))
    ]
    if not priced:
        return []

    # Scored as a pool, so the ranking spreads across whatever you actually own.
    scores = velocity_scores(
        [row["distinct_prices_90d"] for row, _ in priced],
        [row["days_since_price_change"] for row, _ in priced],
    )

    return [
        Candidate(
            copy_id=row["copy_id"],
            variant_id=row["variant_id"],
            card_name=row["card_name"],
            sub_type=row["sub_type"],
            condition_code=row["condition_code"],
            set_name=row["set_name"],
            price_cents=price,
            velocity=score,
        )
        for (row, price), score in zip(priced, scores)
    ]


def build_plan(conn: sqlite3.Connection, channel: str) -> ListingPlan:
    """Choose what to list on one channel, respecting its caps.

    Selection is greedy by velocity per dollar of listed-value cap consumed,
    which is the right ordering when the value cap binds. Optimal 2D knapsack
    is NP-hard and the velocity input is a rough proxy anyway — a more precise
    optimizer over noisy scores would be false precision.

    Cards already live on the channel keep their slot and are not reconsidered.
    """
    ch = conn.execute("SELECT * FROM channels WHERE channel = ?", (channel,)).fetchone()
    if ch is None:
        raise KeyError(f"Unknown channel: {channel}")

    usage = conn.execute(
        "SELECT * FROM channel_usage WHERE channel = ?", (channel,)
    ).fetchone()

    # Two different ceilings can bind, and the lower one is what a plan should
    # respect. `max_listing_count` is what the marketplace refuses to go past.
    # `free_listings_per_period` is where listings stop being free: eBay allows
    # 5,000 items a month but only the first 250 cost nothing, and a Good 'Til
    # Cancelled listing is charged again at every monthly renewal. Planning to
    # the hard cap would quietly sign up for a recurring bill.
    listing_cap = ch["max_listing_count"]
    allowance = ch["free_listings_per_period"]
    if allowance is not None:
        listing_cap = allowance if listing_cap is None else min(listing_cap, allowance)

    value_cap = ch["max_listed_value_cents"]
    item_ceiling = ch["max_item_price_cents"]

    count_headroom = (
        None if listing_cap is None else listing_cap - usage["live_listing_count"]
    )
    value_headroom = (
        None if value_cap is None else value_cap - usage["live_listed_value_cents"]
    )

    selected: list[Candidate] = []
    rejected: list[Rejection] = []

    pool = candidates(conn, channel)

    # Filter on per-card rules first, so cap-driven rejections are not confused
    # with cards that would never qualify anyway.
    eligible: list[Candidate] = []
    for candidate in pool:
        if item_ceiling is not None and candidate.price_cents > item_ceiling:
            rejected.append(
                Rejection(candidate, f"over the ${item_ceiling / 100:,.0f} item ceiling")
            )
            continue

        floor = ec.breakeven_price_cents(conn, channel, cards_in_order=6)
        if candidate.price_cents < floor:
            rejected.append(
                Rejection(candidate, f"under the ${floor / 100:,.2f} breakeven")
            )
            continue

        eligible.append(candidate)

    # Density = velocity per dollar of cap consumed. With no value cap, price is
    # irrelevant to the constraint and raw velocity is the right ordering.
    def density(candidate: Candidate) -> float:
        if value_cap is None:
            return candidate.velocity
        return candidate.velocity / max(candidate.price_cents, 1)

    for candidate in sorted(eligible, key=density, reverse=True):
        if count_headroom is not None and len(selected) >= count_headroom:
            rejected.append(Rejection(candidate, "no listing slots left"))
            continue
        if value_headroom is not None:
            used = sum(c.price_cents for c in selected)
            if used + candidate.price_cents > value_headroom:
                rejected.append(Rejection(candidate, "would exceed the listed-value cap"))
                continue
        selected.append(candidate)

    selected.sort(key=lambda c: c.velocity, reverse=True)
    return ListingPlan(
        channel=channel,
        selected=selected,
        rejected=rejected,
        listing_cap=listing_cap,
        value_cap_cents=value_cap,
    )
