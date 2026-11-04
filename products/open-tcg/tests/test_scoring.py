from __future__ import annotations

import datetime as dt

from radar.stores import collect, registry, scoring

from .conftest import NOW

FIRST = registry.Store(store_id="first", name="First", domain="first.com", tier="first_pass")
EXPLORE = registry.Store(store_id="explore", name="Explore", domain="explore.com", tier="explore")


def test_tier_rules():
    assert scoring._tier(EXPLORE, msrp_hits=2, msrp_offers_now=0, runs=10, failures=0)[:2] == ("hot", 5)
    assert scoring._tier(EXPLORE, msrp_hits=0, msrp_offers_now=3, runs=10, failures=0)[:2] == ("hot", 5)
    assert scoring._tier(EXPLORE, msrp_hits=1, msrp_offers_now=2, runs=10, failures=0)[:2] == ("explore", 60)
    tier, minutes, reason = scoring._tier(FIRST, msrp_hits=5, msrp_offers_now=5, runs=8, failures=4)
    assert (tier, minutes) == ("first_pass", 60) and reason.startswith("failing")  # failing wins over hot
    assert scoring._tier(EXPLORE, msrp_hits=0, msrp_offers_now=0, runs=8, failures=6)[1] == 240  # capped


def _score(connection, store_id, tier, minutes, reason="registry tier"):
    connection.execute(
        """
        INSERT INTO store_scores (store_id, computed_at, matched_listings, in_stock_matched, msrp_offers_now, msrp_hits,
            new_listings, runs, failures, effective_tier, discovery_minutes, reason)
        VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, ?, ?, ?)
        """,
        (store_id, NOW.isoformat(), tier, minutes, reason),
    )


def test_cadence_speeds_up_hot_and_first_pass_in_a_drop_window(connection):
    collect.sync_registry(connection, [FIRST, EXPLORE])
    _score(connection, "first", "hot", 5)
    _score(connection, "explore", "explore", 60)
    assert scoring.cadence(connection, [FIRST, EXPLORE], now=NOW, set_keys={"delta reign"}) == {"first": 5, "explore": 60}
    connection.execute(
        """
        INSERT INTO observations (source_id, external_id, text, signal, is_tcg, received_at)
        VALUES ('bluesky', 'x', 'Delta Reign ETBs live at Target now', 'in_stock', 1, ?)
        """,
        ((NOW - dt.timedelta(minutes=10)).isoformat(),),
    )
    assert scoring.drop_window(connection, now=NOW, set_keys={"delta reign"}) == "bluesky signal: delta reign"
    assert scoring.cadence(connection, [FIRST, EXPLORE], now=NOW, set_keys={"delta reign"}) == {"first": 2, "explore": 60}
    # An hour later the signal has expired; an unwatched set never opens a window.
    later = NOW + dt.timedelta(minutes=75)
    assert scoring.drop_window(connection, now=later, set_keys={"delta reign"}) is None
    assert scoring.drop_window(connection, now=NOW, set_keys={"pitch black"}) is None


def test_release_day_opens_a_drop_window(connection):
    connection.execute("INSERT INTO ref_groups (group_id, name, published_on) VALUES (1, 'ME06: Delta Reign', NULL)")
    local_noon = NOW.astimezone().replace(hour=12)
    connection.execute(
        "INSERT INTO ref_products (product_id, group_id, name, product_type, release_on, updated_at) "
        "VALUES (1, 1, 'Delta Reign Elite Trainer Box', 'etb', ?, '')",
        (local_noon.date().isoformat(),),
    )
    assert scoring.drop_window(connection, now=local_noon, set_keys={"delta reign"}) == "release day: ME06: Delta Reign"
    assert scoring.drop_window(connection, now=local_noon.replace(hour=3), set_keys={"delta reign"}) is None


def test_plan_splits_fast_and_slow_work(connection):
    collect.sync_registry(connection, [FIRST, EXPLORE])
    connection.execute("UPDATE stores SET is_robots_allowed = 1, robots_checked_at = ?", (NOW.isoformat(),))
    cadence = {"first": 5, "explore": 60}
    fast = collect.plan(connection, [FIRST, EXPLORE], NOW, cadence=cadence, mode="fast")
    assert [(p.store.store_id, p.is_discovery_due, p.is_full_sweep) for p in fast] == [("first", True, False)]
    slow = {p.store.store_id: p for p in collect.plan(connection, [FIRST, EXPLORE], NOW, cadence=cadence, mode="slow")}
    assert slow["first"].is_discovery_due is False and slow["first"].is_full_sweep is True  # sweep stays with the sync
    assert slow["explore"].is_discovery_due is True
    # The fast reader skips a store whose robots.txt hasn't allowed reads.
    connection.execute("UPDATE stores SET is_robots_allowed = NULL")
    assert collect.plan(connection, [FIRST], NOW, cadence=cadence, mode="fast") == []


def test_reads_are_counted_per_day(connection):
    collect.sync_registry(connection, [FIRST])
    plan_item = collect.StorePlan(store=FIRST, is_discovery_due=True, is_full_sweep=False,
                                  is_robots_check_due=False, is_collection_check_due=False)
    collect._record_store(connection, collect.StoreOutcome(plan=plan_item, products=[]), NOW)
    collect._record_store(connection, collect.StoreOutcome(plan=plan_item, error="HTTP 500"), NOW)
    row = connection.execute("SELECT runs, failures FROM store_run_days WHERE store_id = 'first'").fetchone()
    assert tuple(row) == (2, 1)


def test_refresh_scores_and_renders(connection):
    collect.sync_registry(connection, [FIRST])
    assert scoring.refresh(connection, [FIRST], now=NOW) is True
    assert scoring.refresh(connection, [FIRST], now=NOW + dt.timedelta(minutes=5)) is False  # not due yet
    row = connection.execute("SELECT effective_tier, discovery_minutes FROM store_scores").fetchone()
    assert tuple(row) == ("first_pass", 15)
    assert "First" in scoring.render(connection, now=NOW)
