"""The founder watchlist is the radar's single input."""

from __future__ import annotations

from radar import watchlist


def test_repo_watchlist_loads_and_is_consistent():
    items = watchlist.load()
    assert len(items) == 18
    assert all(item.alert_at > 0 for item in items)
    assert not any(item.auto_buy for item in items)


def test_watch_set_keys_come_from_item_names():
    keys = watchlist.set_keys_for(
        ["SV: Prismatic Evolutions", "ME: 30th Celebration", "SV: Surging Sparks"],
        [item.name for item in watchlist.load()],
    )
    assert keys == {"prismatic evolutions", "30th celebration"}
