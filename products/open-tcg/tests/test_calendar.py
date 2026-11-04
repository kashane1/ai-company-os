"""Upcoming-release calendar view."""

from __future__ import annotations

from radar import calendar, sources
from radar.catalog import sync

from .conftest import NOW
from .test_catalog_sync import FakeTcgCsv


def test_upcoming_groups_products_by_release_date_with_latest_price(connection):
    sync.sync_catalog(connection, FakeTcgCsv(), now=NOW, watch_set_keys=())
    sources.record_run(connection, "tcgcsv", ok=True, now=NOW)

    days = calendar.upcoming(connection, today=NOW.date())
    by_date = {day.release_on: day for day in days}

    assert set(by_date) == {"2026-11-06", "2026-11-20"}
    nov6 = {item.name: item for item in by_date["2026-11-06"].items}
    box = nov6["Delta Reign Booster Box"]
    assert box.product_type == "booster_box"
    assert box.market_price and box.market_price > 0
    assert nov6["Delta Reign Single Pack Blister (Target Exclusive) [Keldeo]"].exclusive_retailer == "Target"
    assert [item.name for item in by_date["2026-11-20"].items] == ["Delta Reign Build & Battle Box"]


def test_render_mentions_exclusives_and_prices(connection):
    sync.sync_catalog(connection, FakeTcgCsv(), now=NOW, watch_set_keys=())
    text = calendar.render(calendar.upcoming(connection, today=NOW.date()), today=NOW.date())
    assert "Nov 06, 2026" in text
    assert "Target exclusive" in text
    assert "$" in text
