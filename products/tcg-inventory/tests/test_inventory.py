"""Tests for the pieces that silently corrupt inventory when they're wrong.

These do not attach the catalog — none of this logic needs it, and depending on
a 1.5 GB sibling database would make the suite unrunnable on a fresh checkout.
"""

from __future__ import annotations

import pytest
from inventory import db, intake, ledger, slots
from inventory import economics as ec


@pytest.fixture
def conn(tmp_path):
    connection = db.connect(tmp_path / "inventory.db", with_catalog=False)
    db.initialize(connection)
    yield connection
    connection.close()


def make_copy(conn, *, variant_id=1, product_id=42382, condition="NM", cost_cents=100):
    cursor = conn.execute(
        """
        INSERT INTO copies (variant_id, product_id, condition_code, cost_cents)
        VALUES (?, ?, ?, ?)
        """,
        (variant_id, product_id, condition, cost_cents),
    )
    conn.commit()
    return cursor.lastrowid


# ─── Idempotency ─────────────────────────────────────────────────────────────

def test_replayed_notification_does_not_create_a_second_event(conn):
    """The failure this schema exists to prevent: a webhook delivered twice."""
    copy_id = make_copy(conn)
    key = "ebay:order:12-34567-89012:item:445"

    first = ledger.record(conn, copy_id, "sold", channel="ebay", idempotency_key=key)
    second = ledger.record(conn, copy_id, "sold", channel="ebay", idempotency_key=key)

    assert first.was_duplicate is False
    assert second.was_duplicate is True
    assert second.event_id == first.event_id

    total = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE copy_id = ?", (copy_id,)
    ).fetchone()["n"]
    assert total == 1


def test_events_without_a_key_are_not_deduplicated(conn):
    """Two genuine price changes must both be recorded."""
    copy_id = make_copy(conn)
    ledger.record(conn, copy_id, "price_changed", price_cents=300)
    ledger.record(conn, copy_id, "price_changed", price_cents=275)

    total = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE copy_id = ?", (copy_id,)
    ).fetchone()["n"]
    assert total == 2


# ─── State projection ────────────────────────────────────────────────────────

def test_sale_path_moves_through_the_expected_states(conn):
    copy_id = make_copy(conn)

    ledger.record(conn, copy_id, "acquired")
    assert ledger.current_state(conn, copy_id) == "collection"

    ledger.record(conn, copy_id, "slotted", slot_number=1)
    assert ledger.current_state(conn, copy_id) == "in_binder"

    # Listing and selling do not move the card — it is still in its slot.
    ledger.record(conn, copy_id, "listed", channel="tcgplayer", price_cents=1200)
    assert ledger.current_state(conn, copy_id) == "in_binder"
    ledger.record(conn, copy_id, "sold", channel="tcgplayer", price_cents=1200)
    assert ledger.current_state(conn, copy_id) == "in_binder"

    ledger.record(conn, copy_id, "pulled", slot_number=1)
    assert ledger.current_state(conn, copy_id) == "outbound"

    ledger.record(conn, copy_id, "shipped")
    assert ledger.current_state(conn, copy_id) == "in_transit"

    ledger.record(conn, copy_id, "delivered")
    assert ledger.current_state(conn, copy_id) == "sold"


def test_a_copy_can_be_listed_on_two_channels_at_once(conn):
    """Dual-listing is the normal case, so 'listed' must not be a copy state."""
    copy_id = make_copy(conn)
    ledger.record(conn, copy_id, "slotted", slot_number=1)
    ledger.record(conn, copy_id, "listed", channel="tcgplayer", price_cents=1200)
    ledger.record(conn, copy_id, "listed", channel="ebay", price_cents=1400)

    assert ledger.current_state(conn, copy_id) == "in_binder"


# ─── Slots ───────────────────────────────────────────────────────────────────

def test_allocation_takes_the_lowest_free_slot(conn):
    first = make_copy(conn)
    second = make_copy(conn)

    assert slots.next_free_slot(conn) == 1
    ledger.record(conn, first, "slotted", slot_number=1)
    assert slots.next_free_slot(conn) == 2
    ledger.record(conn, second, "slotted", slot_number=2)
    assert slots.next_free_slot(conn) == 3


def test_pulling_a_card_returns_its_slot_to_the_free_list(conn):
    first = make_copy(conn)
    second = make_copy(conn)
    third = make_copy(conn)

    for copy_id, slot in ((first, 1), (second, 2), (third, 3)):
        ledger.record(conn, copy_id, "slotted", slot_number=slot)
    assert slots.next_free_slot(conn) == 4

    ledger.record(conn, second, "pulled", slot_number=2)

    assert slots.next_free_slot(conn) == 2
    assert slots.find_copy(conn, second) is None
    assert slots.capacity(conn)["occupied"] == 2


def test_slot_address_derives_page_and_pocket(conn):
    assert str(slots.address(conn, 1)) == "Binder 1, Page 1, Pocket 1"
    assert str(slots.address(conn, 9)) == "Binder 1, Page 1, Pocket 9"
    assert str(slots.address(conn, 10)) == "Binder 1, Page 2, Pocket 1"
    assert str(slots.address(conn, 47)) == "Binder 1, Page 6, Pocket 2"


def test_binder_full_raises_rather_than_returning_a_bad_slot(conn):
    conn.execute("UPDATE binders SET last_slot = 2 WHERE binder_name = 'Binder 1'")
    conn.commit()

    for slot in (1, 2):
        ledger.record(conn, make_copy(conn), "slotted", slot_number=slot)

    with pytest.raises(slots.BinderFull):
        slots.next_free_slot(conn)


# ─── Economics ───────────────────────────────────────────────────────────────

def test_per_order_costs_amortize_across_a_basket(conn):
    """The reason cheap cards work on TCGplayer and not on eBay."""
    solo = ec.compute_proceeds(conn, "tcgplayer", 300, cards_in_order=1)
    basket = ec.compute_proceeds(conn, "tcgplayer", 300, cards_in_order=8)

    assert basket.net_cash_cents > solo.net_cash_cents
    assert basket.ship_cost_cents < solo.ship_cost_cents
    # Commission is per card and must not be amortized.
    assert basket.commission_cents == solo.commission_cents


def test_ebay_breakeven_is_higher_than_tcgplayer(conn):
    """Driven by listing labor, not by fees — the two fee rates are equal here."""
    assert (
        ec.breakeven_price_cents(conn, "ebay")
        > ec.breakeven_price_cents(conn, "tcgplayer")
    )


def test_raising_the_labor_rate_raises_the_breakeven(conn):
    before = ec.breakeven_price_cents(conn, "ebay")
    db.set_setting(conn, "labor_rate_cents_per_hour", "6000")
    assert ec.breakeven_price_cents(conn, "ebay") > before


def test_cheap_card_is_viable_on_tcgplayer_but_not_ebay(conn):
    verdicts = {
        v.channel: v
        for v in ec.evaluate_channels(conn, 300, cards_in_order={"tcgplayer": 8})
    }
    assert verdicts["tcgplayer"].is_viable
    assert not verdicts["ebay"].is_viable
    assert "breakeven" in verdicts["ebay"].blocked_reason


def test_item_ceiling_blocks_the_channel(conn):
    verdicts = {v.channel: v for v in ec.evaluate_channels(conn, 60000)}
    assert not verdicts["tcgplayer"].is_viable
    assert "ceiling" in verdicts["tcgplayer"].blocked_reason


def test_listed_value_cap_blocks_once_headroom_runs_out(conn):
    """TCGplayer Level 1 stops at $1,000 of listed value, not just 100 listings."""
    copy_id = make_copy(conn)
    conn.execute(
        """
        INSERT INTO listings (copy_id, channel, list_price_cents, listed_at)
        VALUES (?, 'tcgplayer', 99000, datetime('now'))
        """,
        (copy_id,),
    )
    conn.commit()

    verdicts = {v.channel: v for v in ec.evaluate_channels(conn, 5000)}
    assert not verdicts["tcgplayer"].is_viable
    assert "headroom" in verdicts["tcgplayer"].blocked_reason


# ─── Verified channel economics ──────────────────────────────────────────────
# These pin the numbers read off the published fee schedules and Seller Hub on
# 2026-11-02. They exist so that a later edit to seed.sql that quietly reverts
# to an estimate fails loudly instead of silently mispricing the shelf.

def test_ebay_charges_the_small_order_fee_at_or_under_ten_dollars(conn):
    ch = conn.execute("SELECT * FROM channels WHERE channel = 'ebay'").fetchone()

    assert ec.order_fee_cents(ch, 1000) == 30
    assert ec.order_fee_cents(ch, 1001) == 40


def test_tcgplayer_charges_one_flat_order_fee(conn):
    ch = conn.execute("SELECT * FROM channels WHERE channel = 'tcgplayer'").fetchone()

    assert ec.order_fee_cents(ch, 500) == 30
    assert ec.order_fee_cents(ch, 50000) == 30


def test_breakeven_resolves_which_order_fee_it_pays(conn):
    """The fee depends on the order total, which depends on the price solved for."""
    cheap = ec.breakeven_price_cents(conn, "ebay")
    ch = conn.execute("SELECT * FROM channels WHERE channel = 'ebay'").fetchone()

    assert ec.order_fee_cents(ch, cheap) == 30  # it landed under $10 and paid $0.30


def test_ebay_capacity_is_no_longer_the_binding_constraint(conn):
    """The original seed had 10 listings and $500; the real account allows far more."""
    usage = conn.execute("SELECT * FROM channel_usage WHERE channel = 'ebay'").fetchone()

    assert usage["max_listing_count"] == 5000
    assert usage["max_listed_value_cents"] == 5_000_000


def test_the_free_listing_allowance_blocks_before_the_hard_cap(conn):
    """250 free listings is where cost jumps, so that is where a plan should stop."""
    conn.execute(
        "UPDATE channels SET free_listings_per_period = 1 WHERE channel = 'ebay'"
    )
    conn.commit()
    intake.list_copy(conn, make_copy(conn), "ebay", 4705)

    verdict = next(v for v in ec.evaluate_channels(conn, 4705) if v.channel == "ebay")

    assert not verdict.is_viable
    assert "free listings" in verdict.blocked_reason
    assert "$0.35" in verdict.blocked_reason


def test_tcgplayer_has_no_free_listing_allowance_to_exhaust(conn):
    usage = conn.execute(
        "SELECT * FROM channel_usage WHERE channel = 'tcgplayer'"
    ).fetchone()

    assert usage["free_listings_per_period"] is None
    assert usage["insertion_fee_cents"] == 0
