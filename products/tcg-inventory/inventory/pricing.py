"""Repricing live listings, with the brakes on.

The naive version of this — set price to TCGplayer market price, every day —
is a trap for four reasons, and every guard below exists to defuse one of them.

  Market price lags. It is an average of recent *sales*, not of current asks,
  so following it underprices into a rally and overprices into a slide. Nothing
  here fixes that; it is why `price_health` can veto a move outright rather
  than acting confidently on a number that may be describing last month.

  Quoted prices are sometimes not real. TCGplayer pins a price when nothing
  sells, so a stale quote can sit unchanged for 654 days and then step hard.
  Untrustworthy quotes are refused, not followed.

  Small moves are worse than no moves. Repricing on noise churns listings,
  burns quota and resets listing age for nothing, so a deadband suppresses
  anything under a few percent.

  A bad data day can empty the shelf. A daily clamp means the worst a broken
  feed can do is move everything a fifth of the way, once, and get caught.

Nothing auto-applies beyond a configured size. Bigger moves become proposals
for a human, and every applied change is written to `price_changes` with the
rule that caused it, so "why is this card at $3?" always has an answer.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import catalog, economics as ec, ledger


@dataclass(frozen=True)
class Proposal:
    listing_id: int
    copy_id: int
    channel: str
    card_name: str
    condition_code: str

    current_cents: int
    target_cents: int
    proposed_cents: int

    reason: str
    is_auto_applicable: bool
    blockers: tuple[str, ...] = field(default=())

    @property
    def change_pct(self) -> float:
        if self.current_cents == 0:
            return 0.0
        return (self.proposed_cents - self.current_cents) / self.current_cents * 100

    @property
    def is_actionable(self) -> bool:
        return not self.blockers and self.proposed_cents != self.current_cents


def _setting_float(conn: sqlite3.Connection, key: str, default: float) -> float:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return float(row["value"]) if row else default


def price_floor_cents(
    conn: sqlite3.Connection, channel: str, cost_cents: int | None
) -> int:
    """The lowest price that still clears cost, fees and the reserve margin.

    With no cost basis recorded, this falls back to the channel breakeven —
    which protects against listing below handling cost, but not against selling
    at a loss. That is the practical argument for capturing cost at intake.
    """
    reserve = int(_setting_float(conn, "reserve_margin_cents", 100))
    required = (cost_cents or 0) + reserve
    return ec.breakeven_price_cents(conn, channel, min_margin_cents=required)


def propose(conn: sqlite3.Connection, listing_id: int) -> Proposal | None:
    """Work out what one live listing should cost. None if there is no listing."""
    row = conn.execute(
        """
        SELECT l.listing_id, l.copy_id, l.channel, l.list_price_cents,
               c.variant_id, c.condition_code, c.cost_cents,
               s.card_name
          FROM listings l
          JOIN copies c ON c.copy_id = l.copy_id
          JOIN catalog.screener_rows s ON s.variant_id = c.variant_id
         WHERE l.listing_id = ? AND l.ended_at IS NULL
        """,
        (listing_id,),
    ).fetchone()
    if row is None:
        return None

    current = row["list_price_cents"]
    blockers: list[str] = []

    target = catalog.market_price_cents(conn, row["variant_id"], row["condition_code"])
    if not target:
        return Proposal(
            listing_id=row["listing_id"], copy_id=row["copy_id"], channel=row["channel"],
            card_name=row["card_name"], condition_code=row["condition_code"],
            current_cents=current, target_cents=current, proposed_cents=current,
            reason="no market price", is_auto_applicable=False,
            blockers=("catalog has no price for this variant",),
        )

    health = catalog.price_health(conn, row["variant_id"])
    if not health.is_trustworthy:
        blockers.extend(health.warnings)

    proposed = target
    reason = "matched market price"

    floor = price_floor_cents(conn, row["channel"], row["cost_cents"])
    if proposed < floor:
        proposed = floor
        reason = "clamped up to the cost-and-fees floor"

    # Daily clamp, applied last so it bounds whatever the rules produced.
    max_move = _setting_float(conn, "max_daily_move_pct", 20.0)
    ceiling = round(current * (1 + max_move / 100))
    basement = round(current * (1 - max_move / 100))
    if proposed > ceiling:
        proposed, reason = ceiling, f"clamped to +{max_move:.0f}% daily limit"
    elif proposed < basement:
        proposed, reason = basement, f"clamped to -{max_move:.0f}% daily limit"

    deadband = _setting_float(conn, "price_deadband_pct", 3.0)
    move_pct = abs(proposed - current) / current * 100 if current else 100.0
    if move_pct < deadband:
        proposed, reason = current, f"within the {deadband:.0f}% deadband"

    auto_max = _setting_float(conn, "auto_apply_max_pct", 10.0)
    is_auto = not blockers and move_pct <= auto_max

    return Proposal(
        listing_id=row["listing_id"], copy_id=row["copy_id"], channel=row["channel"],
        card_name=row["card_name"], condition_code=row["condition_code"],
        current_cents=current, target_cents=target, proposed_cents=proposed,
        reason=reason, is_auto_applicable=is_auto, blockers=tuple(blockers),
    )


def propose_all(conn: sqlite3.Connection, channel: str | None = None) -> list[Proposal]:
    """Every live listing that wants a different price, biggest move first."""
    rows = conn.execute(
        """
        SELECT listing_id FROM listings
         WHERE ended_at IS NULL AND (? IS NULL OR channel = ?)
        """,
        (channel, channel),
    ).fetchall()

    proposals = [p for row in rows if (p := propose(conn, row["listing_id"]))]
    actionable = [p for p in proposals if p.is_actionable or p.blockers]
    actionable.sort(key=lambda p: abs(p.change_pct), reverse=True)
    return actionable


def apply(conn: sqlite3.Connection, proposal: Proposal, *, was_auto: bool = False) -> None:
    """Commit a price change: the listing, the audit row and the ledger event.

    Refuses a proposal carrying blockers. Overriding one is a deliberate act —
    clear the blocker or change the rule, rather than forcing it here.
    """
    if proposal.blockers:
        raise ValueError(
            f"Listing {proposal.listing_id} is blocked: {'; '.join(proposal.blockers)}"
        )
    if proposal.proposed_cents == proposal.current_cents:
        return

    changed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        "UPDATE listings SET list_price_cents = ? WHERE listing_id = ?",
        (proposal.proposed_cents, proposal.listing_id),
    )
    conn.execute(
        """
        INSERT INTO price_changes
            (listing_id, changed_at, from_cents, to_cents, reason, was_auto_applied)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            proposal.listing_id, changed_at, proposal.current_cents,
            proposal.proposed_cents, proposal.reason, 1 if was_auto else 0,
        ),
    )
    ledger.record(
        conn,
        proposal.copy_id,
        "price_changed",
        channel=proposal.channel,
        price_cents=proposal.proposed_cents,
        occurred_at=changed_at,
        detail={"from_cents": proposal.current_cents, "reason": proposal.reason},
    )


def apply_auto(conn: sqlite3.Connection, channel: str | None = None) -> tuple[int, int]:
    """Apply every proposal small enough to trust. Returns (applied, queued)."""
    applied = queued = 0
    for proposal in propose_all(conn, channel):
        if proposal.is_auto_applicable and proposal.is_actionable:
            apply(conn, proposal, was_auto=True)
            applied += 1
        elif proposal.is_actionable or proposal.blockers:
            queued += 1
    return applied, queued


def history(conn: sqlite3.Connection, listing_id: int) -> list[sqlite3.Row]:
    """Why this listing is the price it is."""
    return conn.execute(
        "SELECT * FROM price_changes WHERE listing_id = ? ORDER BY changed_at",
        (listing_id,),
    ).fetchall()
