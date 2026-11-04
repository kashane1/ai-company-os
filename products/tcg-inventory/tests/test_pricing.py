"""Tests for the repricing guards.

Each one corresponds to a specific way an unguarded repricer loses money.
"""

from __future__ import annotations

import pytest
from inventory import intake, pricing

IONO_SIR = 1       # $47.05, healthy
TOGETIC_STALE = 4  # $49.99, 654 days stale, 1 distinct price


def listed(conn, variant=IONO_SIR, condition="NM", price=4705, cost=None):
    result = intake.add_copy(conn, variant, condition, cost_cents=cost)
    listing_id = intake.list_copy(conn, result.copy_id, "tcgplayer", price)
    return result.copy_id, listing_id


# ─── Core behaviour ──────────────────────────────────────────────────────────

def test_a_listing_above_market_is_proposed_down(conn):
    _, listing_id = listed(conn, price=6000)  # market is $47.05

    proposal = pricing.propose(conn, listing_id)

    assert proposal.proposed_cents < 6000
    assert proposal.is_actionable


def test_no_proposal_for_a_listing_already_at_market(conn):
    _, listing_id = listed(conn, price=4705)

    proposal = pricing.propose(conn, listing_id)

    assert proposal.proposed_cents == 4705
    assert not proposal.is_actionable


def test_an_ended_listing_has_no_proposal(conn):
    _, listing_id = listed(conn)
    intake.end_listing(conn, listing_id, "sold")

    assert pricing.propose(conn, listing_id) is None


# ─── Guards ──────────────────────────────────────────────────────────────────

def test_small_moves_are_suppressed_by_the_deadband(conn):
    """Repricing on noise churns listings and buys nothing."""
    _, listing_id = listed(conn, price=4800)  # ~2% above market

    proposal = pricing.propose(conn, listing_id)

    assert proposal.proposed_cents == 4800
    assert "deadband" in proposal.reason


def test_a_large_drop_is_clamped_to_the_daily_limit(conn):
    """A broken feed must not be able to empty the shelf in one pass."""
    _, listing_id = listed(conn, price=20000)  # market is $47.05

    proposal = pricing.propose(conn, listing_id)

    assert proposal.proposed_cents == 16000  # -20%
    assert "daily limit" in proposal.reason
    assert proposal.target_cents == 4705     # the unclamped target is still visible


def test_a_stale_quote_blocks_the_move(conn):
    """654 days without a price change is not a market price."""
    _, listing_id = listed(conn, variant=TOGETIC_STALE, price=9000)

    proposal = pricing.propose(conn, listing_id)

    assert proposal.blockers
    assert not proposal.is_auto_applicable
    assert any("hasn't moved" in b for b in proposal.blockers)


def test_price_never_goes_below_cost_plus_fees(conn):
    """The guard that stops an automated repricer selling at a loss."""
    conn.execute("UPDATE settings SET value = '100' WHERE key = 'max_daily_move_pct'")
    conn.commit()
    _, listing_id = listed(conn, variant=IONO_SIR, price=10000, cost=9000)

    proposal = pricing.propose(conn, listing_id)

    floor = pricing.price_floor_cents(conn, "tcgplayer", 9000)
    assert proposal.proposed_cents >= floor
    assert proposal.proposed_cents > 9000
    assert "floor" in proposal.reason


def test_floor_falls_back_to_breakeven_without_a_cost_basis(conn):
    with_cost = pricing.price_floor_cents(conn, "tcgplayer", 5000)
    without = pricing.price_floor_cents(conn, "tcgplayer", None)

    assert with_cost > without
    assert without > 0


# ─── Review queue ────────────────────────────────────────────────────────────

def test_small_moves_auto_apply_and_large_ones_queue(conn):
    conn.execute("UPDATE settings SET value = '10.0' WHERE key = 'auto_apply_max_pct'")
    conn.commit()
    listed(conn, price=5100)   # ~8% over market -> auto
    listed(conn, price=8000)   # ~41% over market -> queue

    applied, queued = pricing.apply_auto(conn)

    assert applied == 1
    assert queued == 1


def test_blocked_proposals_are_never_auto_applied(conn):
    listed(conn, variant=TOGETIC_STALE, price=9000)

    applied, queued = pricing.apply_auto(conn)

    assert applied == 0
    assert queued == 1


def test_applying_a_blocked_proposal_raises(conn):
    _, listing_id = listed(conn, variant=TOGETIC_STALE, price=9000)
    proposal = pricing.propose(conn, listing_id)

    with pytest.raises(ValueError):
        pricing.apply(conn, proposal)


# ─── Audit ───────────────────────────────────────────────────────────────────

def test_applying_records_why_the_price_changed(conn):
    """So "why is this card at $3?" is answerable months later."""
    copy_id, listing_id = listed(conn, price=6000)
    proposal = pricing.propose(conn, listing_id)

    pricing.apply(conn, proposal, was_auto=True)

    rows = pricing.history(conn, listing_id)
    assert len(rows) == 1
    assert rows[0]["from_cents"] == 6000
    assert rows[0]["to_cents"] == proposal.proposed_cents
    assert rows[0]["reason"]
    assert rows[0]["was_auto_applied"] == 1

    events = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE copy_id = ? AND kind = 'price_changed'",
        (copy_id,),
    ).fetchone()["n"]
    assert events == 1


def test_applying_updates_the_live_listing(conn):
    _, listing_id = listed(conn, price=6000)
    proposal = pricing.propose(conn, listing_id)

    pricing.apply(conn, proposal)

    price = conn.execute(
        "SELECT list_price_cents FROM listings WHERE listing_id = ?", (listing_id,)
    ).fetchone()["list_price_cents"]
    assert price == proposal.proposed_cents


def test_proposals_are_ordered_by_how_badly_priced_they_are(conn):
    listed(conn, price=5200)
    listed(conn, price=9000)

    proposals = pricing.propose_all(conn)

    assert abs(proposals[0].change_pct) >= abs(proposals[-1].change_pct)
