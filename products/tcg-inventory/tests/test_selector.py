"""Tests for listing selection under channel caps."""

from __future__ import annotations

from inventory import intake, selector

IONO_SIR = 1       # $47.05
IONO_COMMON = 2    # $0.30
CHARIZARD = 3      # $300.29
TOGETIC_STALE = 4  # $49.99, 654 days stale, 1 distinct price
PIDGEY = 5         # $0.25


# ─── Scoring ─────────────────────────────────────────────────────────────────

def test_scores_spread_across_the_pool():
    """Regression: an absolute formula saturated at 1.0 for most of a pool.

    77% of a realistic pool has a price change within the last week, so any
    absolute freshness curve pins three cards in four at the top and the
    ranking silently collapses to price order.
    """
    movement = [5, 8, 14, 29, 45, 63]
    staleness = [1, 1, 2, 7, 17, 187]

    scores = selector.velocity_scores(movement, staleness)

    assert len(set(scores)) > 1, "scores must discriminate"
    assert max(scores) > min(scores) + 0.4, "spread should be meaningful"
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_more_price_movement_outranks_less():
    scores = selector.velocity_scores([1, 60], [5, 5])
    assert scores[1] > scores[0]


def test_a_stale_quote_ranks_below_a_fresh_one():
    scores = selector.velocity_scores([20, 20], [600, 1])
    assert scores[1] > scores[0]


def test_identical_cards_score_identically():
    scores = selector.velocity_scores([10, 10, 10], [5, 5, 5])
    assert len(set(scores)) == 1


def test_missing_metrics_rank_last():
    scores = selector.velocity_scores([30, None], [2, None])
    assert scores[0] > scores[1]


# ─── Plan construction ───────────────────────────────────────────────────────

def test_plan_respects_the_listing_count_cap(conn):
    conn.execute("UPDATE channels SET max_listing_count = 2 WHERE channel = 'tcgplayer'")
    conn.commit()
    for _ in range(5):
        intake.add_copy(conn, IONO_SIR, "NM")

    plan = selector.build_plan(conn, "tcgplayer")

    assert plan.listing_count == 2
    assert any("no listing slots left" in r.reason for r in plan.rejected)


def test_plan_respects_the_listed_value_cap(conn):
    """TCGplayer Level 1 stops at $1,000 of value, not just 100 listings."""
    conn.execute(
        "UPDATE channels SET max_listing_count = 100, max_listed_value_cents = 10000 "
        "WHERE channel = 'tcgplayer'"
    )
    conn.commit()
    for _ in range(6):
        intake.add_copy(conn, IONO_SIR, "NM")  # $47.05 each

    plan = selector.build_plan(conn, "tcgplayer")

    assert plan.value_cents <= 10000
    assert plan.listing_count == 2
    assert any("listed-value cap" in r.reason for r in plan.rejected)


def test_cards_over_the_item_ceiling_are_excluded(conn):
    intake.add_copy(conn, CHARIZARD, "NM")  # $300.29, over a $500 ceiling? no
    conn.execute(
        "UPDATE channels SET max_item_price_cents = 10000 WHERE channel = 'tcgplayer'"
    )
    conn.commit()

    plan = selector.build_plan(conn, "tcgplayer")

    assert plan.listing_count == 0
    assert any("item ceiling" in r.reason for r in plan.rejected)


def test_cards_under_breakeven_are_excluded(conn):
    intake.add_copy(conn, PIDGEY, "NM")  # $0.25

    plan = selector.build_plan(conn, "ebay")

    assert plan.listing_count == 0
    assert any("breakeven" in r.reason for r in plan.rejected)


def test_already_live_cards_are_not_reconsidered(conn):
    result = intake.add_copy(conn, IONO_SIR, "NM")
    intake.list_copy(conn, result.copy_id, "tcgplayer", 4705)

    plan = selector.build_plan(conn, "tcgplayer")

    assert result.copy_id not in {c.copy_id for c in plan.selected}


def test_a_card_live_on_one_channel_can_still_be_planned_for_the_other(conn):
    """Dual-listing is the point — the channels have independent budgets."""
    result = intake.add_copy(conn, IONO_SIR, "NM")
    intake.list_copy(conn, result.copy_id, "tcgplayer", 4705)

    plan = selector.build_plan(conn, "ebay")

    assert result.copy_id in {c.copy_id for c in plan.selected}


def test_sold_and_outbound_cards_are_not_candidates(conn):
    result = intake.add_copy(conn, IONO_SIR, "NM")
    intake.pull_copy(conn, result.copy_id)  # now outbound

    plan = selector.build_plan(conn, "tcgplayer")

    assert result.copy_id not in {c.copy_id for c in plan.selected}


def test_plan_prefers_liquid_cards_at_similar_prices(conn):
    """Togetic and Iono are both ~$47-50; Togetic has been stale for 654 days."""
    liquid = intake.add_copy(conn, IONO_SIR, "NM")      # 46 distinct prices
    stale = intake.add_copy(conn, TOGETIC_STALE, "NM")  # 1 distinct price
    conn.execute("UPDATE channels SET max_listing_count = 1 WHERE channel = 'tcgplayer'")
    conn.commit()

    plan = selector.build_plan(conn, "tcgplayer")

    assert [c.copy_id for c in plan.selected] == [liquid.copy_id]
    assert stale.copy_id in {r.candidate.copy_id for r in plan.rejected}
