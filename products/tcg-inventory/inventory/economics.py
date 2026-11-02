"""Net proceeds, and which channel a card belongs on.

The headline fee rates on TCGplayer and eBay are within pennies of each other,
so fees are not what decides where a card goes. Two other things do:

  Labor. TCGplayer lists against a stock image in about 30 seconds. eBay needs
  photos, a title and item specifics — call it five minutes. On a $3 card that
  difference is the entire margin.

  Capacity. A new account's caps are small and the slots are rivalrous: one of
  ten monthly eBay listings spent on a $3 card is a slot not spent on a $45 one.

Both are modeled as data in `channels`, so the threshold where a card stops
being worth listing is computed, never hardcoded. Speed the listing flow up and
the threshold falls on its own — which makes it a decent measure of whether the
tooling is earning its keep.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass

DEFAULT_LABOR_RATE_CENTS_PER_HOUR = 2500
DEFAULT_MIN_MARGIN_CENTS = 50


@dataclass(frozen=True)
class Proceeds:
    """A full cost breakdown for selling one card on one channel."""

    channel: str
    list_price_cents: int

    commission_cents: int
    order_fee_cents: int
    ship_cost_cents: int
    materials_cents: int
    labor_cents: int
    handling_minutes: float

    @property
    def cash_cost_cents(self) -> int:
        """Everything that actually leaves your pocket, labor excluded."""
        return (
            self.commission_cents
            + self.order_fee_cents
            + self.ship_cost_cents
            + self.materials_cents
        )

    @property
    def net_cash_cents(self) -> int:
        """Cash in hand. This is the number that shows up in your payout."""
        return self.list_price_cents - self.cash_cost_cents

    @property
    def net_after_labor_cents(self) -> int:
        """Cash in hand minus what your time was worth. Can be negative."""
        return self.net_cash_cents - self.labor_cents

    @property
    def margin_rate(self) -> float:
        if self.list_price_cents <= 0:
            return 0.0
        return self.net_cash_cents / self.list_price_cents

    @property
    def effective_hourly_cents(self) -> float:
        """What this sale pays per hour of handling."""
        minutes = self.handling_minutes
        if minutes <= 0:
            return float("inf")
        return self.net_cash_cents * 60.0 / minutes


def _labor_rate(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'labor_rate_cents_per_hour'"
    ).fetchone()
    return int(row["value"]) if row else DEFAULT_LABOR_RATE_CENTS_PER_HOUR


def _min_margin(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'min_margin_cents'"
    ).fetchone()
    return int(row["value"]) if row else DEFAULT_MIN_MARGIN_CENTS


def compute_proceeds(
    conn: sqlite3.Connection,
    channel: str,
    list_price_cents: int,
    *,
    cards_in_order: int = 1,
) -> Proceeds:
    """Break down what one card at one price nets on one channel.

    `cards_in_order` amortizes the per-order costs — the order fee, the postage
    and the envelope are charged once per basket, not once per card. This is
    the whole reason cheap cards work on TCGplayer and not on eBay: a TCGplayer
    buyer takes eight commons in one order, while eight eBay sales are eight
    separate orders, each paying full freight. Shipping labor amortizes the
    same way; listing labor does not, since every card is listed individually.
    """
    if cards_in_order < 1:
        raise ValueError("cards_in_order must be at least 1")

    ch = conn.execute("SELECT * FROM channels WHERE channel = ?", (channel,)).fetchone()
    if ch is None:
        raise KeyError(f"Unknown channel: {channel}")

    share = 1.0 / cards_in_order
    labor_rate = _labor_rate(conn)

    handling_minutes = ch["minutes_to_list"] + ch["minutes_to_ship"] * share
    labor_cents = round(handling_minutes * labor_rate / 60.0)

    return Proceeds(
        channel=channel,
        list_price_cents=list_price_cents,
        commission_cents=round(list_price_cents * ch["fee_rate"]),
        order_fee_cents=round(ch["order_fee_cents"] * share),
        ship_cost_cents=round(ch["ship_cost_cents"] * share),
        materials_cents=round(ch["materials_cents"] * share),
        labor_cents=labor_cents,
        handling_minutes=handling_minutes,
    )


def breakeven_price_cents(
    conn: sqlite3.Connection,
    channel: str,
    *,
    cards_in_order: int = 1,
    min_margin_cents: int | None = None,
) -> int:
    """The lowest price at which listing on this channel is worth doing.

    Solves net_after_labor >= min_margin for price:

        p(1 - fee_rate) - order_fee - ship - materials - labor >= margin

    This is the number that decides whether a card goes on eBay at all, and it
    moves whenever the fee rates, the labor rate or the listing flow change.
    """
    ch = conn.execute("SELECT * FROM channels WHERE channel = ?", (channel,)).fetchone()
    if ch is None:
        raise KeyError(f"Unknown channel: {channel}")

    margin = _min_margin(conn) if min_margin_cents is None else min_margin_cents
    share = 1.0 / cards_in_order
    labor_rate = _labor_rate(conn)

    fixed = (
        ch["order_fee_cents"] * share
        + ch["ship_cost_cents"] * share
        + ch["materials_cents"] * share
        + (ch["minutes_to_list"] + ch["minutes_to_ship"] * share) * labor_rate / 60.0
    )
    return math.ceil((margin + fixed) / (1 - ch["fee_rate"]))


@dataclass(frozen=True)
class ChannelVerdict:
    channel: str
    proceeds: Proceeds
    is_viable: bool
    blocked_reason: str | None


def evaluate_channels(
    conn: sqlite3.Connection,
    list_price_cents: int,
    *,
    cards_in_order: dict[str, int] | None = None,
) -> list[ChannelVerdict]:
    """Score every enabled channel for a card at a given price, best net first.

    A channel is non-viable when the card is worth less than the breakeven
    price, when it exceeds the per-item ceiling, or when the account has no
    capacity left. Capacity is a real blocker, not a rounding error: TCGplayer
    Level 1 stops at 100 listings and $1,000 of listed value.
    """
    cards_in_order = cards_in_order or {}
    verdicts: list[ChannelVerdict] = []

    for ch in conn.execute("SELECT * FROM channels WHERE is_enabled = 1"):
        channel = ch["channel"]
        basket = cards_in_order.get(channel, 1)
        proceeds = compute_proceeds(conn, channel, list_price_cents, cards_in_order=basket)

        reason: str | None = None

        ceiling = ch["max_item_price_cents"]
        if ceiling is not None and list_price_cents > ceiling:
            reason = f"over the ${ceiling / 100:,.0f} per-item ceiling"

        if reason is None:
            floor = breakeven_price_cents(conn, channel, cards_in_order=basket)
            if list_price_cents < floor:
                reason = f"below the ${floor / 100:,.2f} breakeven"

        if reason is None:
            usage = conn.execute(
                "SELECT * FROM channel_usage WHERE channel = ?", (channel,)
            ).fetchone()
            if usage:
                max_count = usage["max_listing_count"]
                max_value = usage["max_listed_value_cents"]
                if max_count is not None and usage["live_listing_count"] >= max_count:
                    reason = f"at the {max_count}-listing cap"
                elif (
                    max_value is not None
                    and usage["live_listed_value_cents"] + list_price_cents > max_value
                ):
                    headroom = max_value - usage["live_listed_value_cents"]
                    reason = f"only ${headroom / 100:,.2f} of listed-value headroom left"

        verdicts.append(
            ChannelVerdict(
                channel=channel,
                proceeds=proceeds,
                is_viable=reason is None,
                blocked_reason=reason,
            )
        )

    verdicts.sort(key=lambda v: (not v.is_viable, -v.proceeds.net_after_labor_cents))
    return verdicts
