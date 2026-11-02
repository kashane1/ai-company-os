"""Tests for intake, cost allocation and the listing lifecycle."""

from __future__ import annotations

import pytest
from inventory import catalog, intake, ledger, slots

IONO_SIR = 1       # $47.05 Holofoil
IONO_COMMON = 2    # $0.30 Normal
CHARIZARD = 3      # $300.29
TOGETIC_STALE = 4  # $49.99, price pinned for 654 days


# ─── Intake ──────────────────────────────────────────────────────────────────

def test_add_copy_records_the_card_and_slots_it(conn):
    result = intake.add_copy(conn, IONO_SIR, "NM", cost_cents=500)

    assert result.card_name == "Iono"
    assert result.sub_type == "Holofoil"
    assert result.market_price_cents == 4705
    assert result.slot is not None
    assert str(result.slot) == "Binder 1, Page 1, Pocket 1"
    assert ledger.current_state(conn, result.copy_id) == "in_binder"


def test_keeper_cards_are_tracked_without_consuming_binder_capacity(conn):
    result = intake.add_copy(conn, CHARIZARD, "NM", assign_slot=False)

    assert result.slot is None
    assert ledger.current_state(conn, result.copy_id) == "collection"
    assert slots.capacity(conn)["occupied"] == 0


def test_condition_haircuts_the_market_price(conn):
    near_mint = intake.add_copy(conn, IONO_SIR, "NM")
    played = intake.add_copy(conn, IONO_SIR, "MP")

    assert near_mint.market_price_cents == 4705
    assert played.market_price_cents == round(4705 * 0.70)


def test_unknown_variant_is_rejected(conn):
    with pytest.raises(intake.NoCatalogEntry):
        intake.add_copy(conn, 9999, "NM")


def test_stale_quote_is_flagged_as_untrustworthy(conn):
    """A price pinned for 654 days is not a market price."""
    health = catalog.price_health(conn, TOGETIC_STALE)

    assert health.is_trustworthy is False
    assert any("hasn't moved" in w for w in health.warnings)
    assert any("illiquid" in w for w in health.warnings)


# ─── Cost basis ──────────────────────────────────────────────────────────────

def test_lot_allocation_sums_exactly_to_the_lot_total(conn):
    """Rounding each share independently loses cents; basis has to tie out."""
    lot = intake.create_acquisition(conn, "2026-11-01", 40000, source="collection buy")
    for variant in (IONO_SIR, IONO_COMMON, CHARIZARD, TOGETIC_STALE):
        intake.add_copy(conn, variant, "NM", acquisition_id=lot)

    allocated = intake.allocate_lot_cost(conn, lot)

    assert sum(allocated.values()) == 40000
    assert len(allocated) == 4


def test_lot_allocation_is_proportional_to_market_value(conn):
    lot = intake.create_acquisition(conn, "2026-11-01", 10000)
    expensive = intake.add_copy(conn, CHARIZARD, "NM", acquisition_id=lot)
    cheap = intake.add_copy(conn, IONO_COMMON, "NM", acquisition_id=lot)

    allocated = intake.allocate_lot_cost(conn, lot)

    assert allocated[expensive.copy_id] > allocated[cheap.copy_id]
    # $300.29 vs $0.30 — the cheap card should get almost nothing.
    assert allocated[cheap.copy_id] < 20


def test_allocation_sums_exactly_with_awkward_rounding(conn):
    """Three equal cards against a total that does not divide by three."""
    lot = intake.create_acquisition(conn, "2026-11-01", 1000)
    for _ in range(3):
        intake.add_copy(conn, IONO_SIR, "NM", acquisition_id=lot)

    allocated = intake.allocate_lot_cost(conn, lot)

    assert sum(allocated.values()) == 1000
    assert sorted(allocated.values()) == [333, 333, 334]


def test_allocation_writes_cost_back_to_the_copies(conn):
    lot = intake.create_acquisition(conn, "2026-11-01", 5000)
    result = intake.add_copy(conn, IONO_SIR, "NM", acquisition_id=lot)

    intake.allocate_lot_cost(conn, lot)

    cost = conn.execute(
        "SELECT cost_cents FROM copies WHERE copy_id = ?", (result.copy_id,)
    ).fetchone()["cost_cents"]
    assert cost == 5000


# ─── Listing lifecycle ───────────────────────────────────────────────────────

def test_a_copy_can_be_listed_on_both_channels(conn):
    result = intake.add_copy(conn, CHARIZARD, "NM")
    intake.list_copy(conn, result.copy_id, "tcgplayer", 30029)
    intake.list_copy(conn, result.copy_id, "ebay", 32000)

    live = intake.live_listings(conn, result.copy_id)
    assert {row["channel"] for row in live} == {"tcgplayer", "ebay"}
    assert ledger.current_state(conn, result.copy_id) == "in_binder"


def test_double_listing_the_same_channel_is_rejected(conn):
    result = intake.add_copy(conn, CHARIZARD, "NM")
    intake.list_copy(conn, result.copy_id, "ebay", 32000)

    with pytest.raises(intake.AlreadyListed):
        intake.list_copy(conn, result.copy_id, "ebay", 31000)


def test_a_sale_closes_the_listing_but_leaves_the_card_in_its_slot(conn):
    result = intake.add_copy(conn, CHARIZARD, "NM")
    listing_id = intake.list_copy(conn, result.copy_id, "tcgplayer", 30029)

    intake.end_listing(conn, listing_id, "sold")

    assert intake.live_listings(conn, result.copy_id) == []
    assert ledger.current_state(conn, result.copy_id) == "in_binder"
    assert slots.find_copy(conn, result.copy_id) is not None


def test_replayed_sale_notification_closes_the_listing_exactly_once(conn):
    """The bug this guards: an event written while the listing stayed open."""
    result = intake.add_copy(conn, CHARIZARD, "NM")
    listing_id = intake.list_copy(conn, result.copy_id, "ebay", 32000)
    key = "ebay:order:12-34567-89012"

    intake.end_listing(conn, listing_id, "sold", idempotency_key=key)
    intake.end_listing(conn, listing_id, "sold", idempotency_key=key)

    row = conn.execute(
        "SELECT ended_at, end_reason FROM listings WHERE listing_id = ?", (listing_id,)
    ).fetchone()
    assert row["ended_at"] is not None
    assert row["end_reason"] == "sold"

    sold_events = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE copy_id = ? AND kind = 'sold'",
        (result.copy_id,),
    ).fetchone()["n"]
    assert sold_events == 1


def test_pulling_frees_the_slot_for_the_next_card(conn):
    first = intake.add_copy(conn, IONO_SIR, "NM")
    second = intake.add_copy(conn, CHARIZARD, "NM")
    assert second.slot.slot_number == 2

    intake.pull_copy(conn, first.copy_id)

    assert ledger.current_state(conn, first.copy_id) == "outbound"
    third = intake.add_copy(conn, IONO_COMMON, "NM")
    assert third.slot.slot_number == 1
