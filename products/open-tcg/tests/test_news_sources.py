"""Southern Hobby distributor list and PokeBeach RSS: parsing and change events."""

from __future__ import annotations

import datetime as dt

from radar import sources
from radar.feeds import pokebeach, southern_hobby

from .conftest import NOW, load_text


def events(connection, kind: str) -> list:
    return connection.execute("SELECT * FROM calendar_events WHERE kind = ?", (kind,)).fetchall()


# ---------------------------------------------------------------------------
# Southern Hobby
# ---------------------------------------------------------------------------


def test_parses_listing_rows_with_release_and_order_due_dates():
    items = southern_hobby.parse_listing(load_text("southern_hobby_page.html"))
    by_item = {item.item_no: item for item in items}
    assert len(items) == 3
    build_and_battle = by_item["NDPKME6BB"]
    assert build_and_battle.name == "Pokemon Mega Evolution 6 Delta Reign Build and Battle Box"
    assert build_and_battle.release_on == "2026-11-20"
    assert build_and_battle.order_due_on == "2026-09-06"
    assert build_and_battle.url.endswith("/p81788/")
    assert by_item["NDPK10458"].name == "Pokemon TCG: Premium Collection - Unova's Heavy Hitters"


def run_southern_hobby(connection, pages, now):
    southern_hobby.sync(connection, fetch_page=lambda page: pages.get(page, ""), now=now)
    sources.record_run(connection, "southern_hobby", ok=True, now=now)


def test_first_southern_hobby_run_is_a_silent_baseline(connection):
    run_southern_hobby(connection, {1: load_text("southern_hobby_page.html")}, NOW)
    assert connection.execute("SELECT COUNT(*) FROM distributor_items").fetchone()[0] == 3
    assert events(connection, "distributor_listed") == []


def test_new_items_and_date_changes_emit_events_once(connection):
    page = load_text("southern_hobby_page.html")
    run_southern_hobby(connection, {1: page}, NOW)

    later = NOW + dt.timedelta(days=1)
    changed = page.replace("11/20/2026", "11/27/2026").replace("NDPK10458", "NDPK99999")
    run_southern_hobby(connection, {1: changed}, later)
    run_southern_hobby(connection, {1: changed}, later)

    listed = events(connection, "distributor_listed")
    assert [row["subject_key"] for row in listed] == ["NDPK99999"]
    moved = events(connection, "release_date_changed")
    assert len(moved) == 1
    assert moved[0]["value"] == "2026-11-20 -> 2026-11-27"


def test_pagination_stops_at_the_first_empty_page(connection):
    requested: list[int] = []

    def fetch_page(page: int) -> str:
        requested.append(page)
        return load_text("southern_hobby_page.html") if page == 1 else "<html></html>"

    southern_hobby.sync(connection, fetch_page=fetch_page, now=NOW)
    assert requested == [1, 2]


# ---------------------------------------------------------------------------
# PokeBeach
# ---------------------------------------------------------------------------


def test_parses_rss_items():
    items = pokebeach.parse_feed(load_text("pokebeach.rss"))
    assert len(items) == 3
    first = items[0]
    assert first.item_key == "157060"
    assert first.title.startswith("New Pokemon TCG Premium Binders")
    assert first.published_at == "2026-09-26T04:12:37+00:00"
    assert first.link.startswith("https://")


def test_product_news_flag_matches_release_and_reveal_titles():
    assert pokebeach.is_product_news("20+ “Delta Reign” Card Images Revealed!")
    assert pokebeach.is_product_news("New Pokemon TCG Premium Binders to Release Featuring Numbered Pokedex Slots")
    assert not pokebeach.is_product_news("The Best Competitive Cards from Pokémon TCG: 30th Celebration")


def test_pokebeach_emits_news_events_only_after_baseline(connection):
    feed = load_text("pokebeach.rss")
    pokebeach.sync(connection, fetch_feed=lambda: feed, now=NOW)
    sources.record_run(connection, "pokebeach_rss", ok=True, now=NOW)
    assert events(connection, "news_posted") == []

    newer = feed.replace(">157060</guid>", ">157099</guid>")
    later = NOW + dt.timedelta(minutes=15)
    pokebeach.sync(connection, fetch_feed=lambda: newer, now=later)
    pokebeach.sync(connection, fetch_feed=lambda: newer, now=later)

    posted = events(connection, "news_posted")
    assert [row["subject_key"] for row in posted] == ["157099"]
