"""Restock episodes: dedupe across sources, lag, scorecard, notifications, manual log."""

from __future__ import annotations

import datetime as dt
import json

from radar import episodes, manual, notify, watchlist

from .conftest import NOW

WATCH = watchlist.load()
SET_KEYS = ["30th celebration", "ascended heroes", "prismatic evolutions", "destined rivals"]


def observe(connection, *, source_id, external_id, text, minutes_after=0, signal="in_stock",
            retailer="Target", watch=("30th Celebration Elite Trainer Box",), is_tcg=True, price=None):
    at = NOW + dt.timedelta(minutes=minutes_after)
    cursor = connection.execute(
        """
        INSERT INTO observations (source_id, external_id, text, signal, retailer, product_text, price,
                                  is_tcg, watch_matches, source_time, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (source_id, external_id, text, signal, retailer, text, price, int(is_tcg), json.dumps(list(watch)),
         at.isoformat(), at.isoformat()),
    )
    connection.commit()
    return cursor.lastrowid


class RecordingNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def __call__(self, title: str, body: str) -> None:
        self.sent.append((title, body))


def test_reports_of_one_restock_from_several_sources_form_one_episode_with_lags(connection):
    first = observe(connection, source_id="bluesky", external_id="a", text="30th Celebration ETB in stock at Target")
    second = observe(connection, source_id="nowinstock_email", external_id="b", text="30th Celebration Elite Trainer Box : Target", minutes_after=3)
    episode_a = episodes.assign(connection, first)
    episode_b = episodes.assign(connection, second)

    assert len(episode_a) == 1 and episode_a == episode_b
    rows = connection.execute("SELECT source_id, lag_s FROM episode_observations ORDER BY lag_s").fetchall()
    assert [(row["source_id"], row["lag_s"]) for row in rows] == [("bluesky", 0), ("nowinstock_email", 180)]


def test_a_later_restock_outside_the_window_is_a_new_episode(connection):
    first = observe(connection, source_id="bluesky", external_id="a", text="30th Celebration ETB in stock at Target")
    later = observe(connection, source_id="bluesky", external_id="c", text="30th Celebration ETB restock at Target", minutes_after=180)
    assert episodes.assign(connection, first) != episodes.assign(connection, later)


def test_different_retailers_are_different_episodes(connection):
    target = observe(connection, source_id="bluesky", external_id="a", text="ETB at Target")
    walmart = observe(connection, source_id="bluesky", external_id="b", text="ETB at Walmart", retailer="Walmart")
    assert episodes.assign(connection, target) != episodes.assign(connection, walmart)


def test_assigning_twice_is_idempotent(connection):
    observation = observe(connection, source_id="bluesky", external_id="a", text="ETB at Target")
    assert episodes.assign(connection, observation) == episodes.assign(connection, observation)
    assert connection.execute("SELECT COUNT(*) FROM episode_observations").fetchone()[0] == 1


def test_non_tcg_posts_do_not_form_episodes(connection):
    observation = observe(connection, source_id="bluesky", external_id="a", text="Plush up at Pokemon Center",
                          watch=(), is_tcg=False)
    assert episodes.assign(connection, observation) == []


def test_watched_availability_notifies_once_per_episode(connection):
    notifier = RecordingNotifier()
    first = observe(connection, source_id="bluesky", external_id="a", text="30th Celebration ETB in stock at Target")
    second = observe(connection, source_id="nowinstock_email", external_id="b", text="30th Celebration ETB : Target", minutes_after=2)
    for observation in (first, second):
        for episode_id in episodes.assign(connection, observation):
            notify.maybe_notify(connection, episode_id, now=NOW + dt.timedelta(minutes=2), send=notifier)

    assert len(notifier.sent) == 1
    title, body = notifier.sent[0]
    assert "30th Celebration Elite Trainer Box" in title
    assert "Target" in title and "in stock" in body.lower()


def test_announcements_and_stale_posts_do_not_notify(connection):
    notifier = RecordingNotifier()
    scheduled = observe(connection, source_id="bluesky", external_id="a", text="Drawing opens tomorrow", signal="drawing_scheduled")
    old = observe(connection, source_id="bluesky", external_id="b", text="ETB at Walmart", retailer="Walmart")
    for observation in (scheduled, old):
        for episode_id in episodes.assign(connection, observation):
            notify.maybe_notify(connection, episode_id, now=NOW + dt.timedelta(hours=2), send=notifier)
    assert notifier.sent == []


def test_prices_above_the_watch_threshold_do_not_notify(connection):
    notifier = RecordingNotifier()
    pricey = observe(connection, source_id="bluesky", external_id="a", text="30th Celebration ETB $89.99 at Amazon",
                     retailer="Amazon", price=89.99)
    for episode_id in episodes.assign(connection, pricey):
        notify.maybe_notify(connection, episode_id, now=NOW, send=notifier, watch=WATCH)
    assert notifier.sent == []  # alert_at for this item is $60


def test_scorecard_reports_first_counts_lag_and_accuracy(connection):
    for index, lag in enumerate((0, 5)):
        observe(connection, source_id="bluesky", external_id=f"b{index}", text="ETB at Target",
                minutes_after=index * 300)
        observe(connection, source_id="guppy", external_id=f"g{index}", text="ETB at Target",
                minutes_after=index * 300 + lag)
    for (observation_id,) in connection.execute("SELECT id FROM observations ORDER BY id").fetchall():
        episodes.assign(connection, observation_id)
    episode_ids = [row[0] for row in connection.execute("SELECT id FROM episodes ORDER BY id")]
    episodes.set_verdict(connection, episode_ids[0], "real")
    episodes.set_verdict(connection, episode_ids[1], "false")

    card = {row.source_id: row for row in episodes.scorecard(connection)}
    assert card["bluesky"].episodes == 2 and card["bluesky"].first == 2
    assert card["guppy"].first == 1  # tied on the first episode (lag 0)
    assert card["guppy"].median_lag_s == 300
    assert card["bluesky"].accuracy == 0.5


def test_manual_guppy_log_joins_the_same_episode(connection):
    post = observe(connection, source_id="bluesky", external_id="a", text="30th Celebration ETB in stock at Target")
    episodes.assign(connection, post)
    logged = manual.log(connection, kind="guppy", text="30th Celebration ETB at Target",
                        at=NOW + dt.timedelta(minutes=1), watch=WATCH, set_keys=SET_KEYS, now=NOW)
    episode_ids = episodes.assign(connection, logged)
    assert len(episode_ids) == 1
    lag = connection.execute(
        "SELECT lag_s FROM episode_observations WHERE observation_id = ?", (logged,)
    ).fetchone()["lag_s"]
    assert lag == 60


def test_scorecard_scores_each_bluesky_account_separately(connection):
    from radar.config import BLUESKY_ACCOUNTS

    dids = list(BLUESKY_ACCOUNTS.values())
    for index, (did, minutes) in enumerate(((dids[0], 0), (dids[1], 4))):
        observation_id = observe(connection, source_id="bluesky", external_id=f"x{index}",
                                 text="30th Celebration ETB in stock at Target", minutes_after=minutes)
        connection.execute("UPDATE observations SET author = ? WHERE id = ?", (did, observation_id))
        connection.commit()
        episodes.assign(connection, observation_id)
    card = {row.source_id: row for row in episodes.scorecard(connection)}
    assert card["bluesky:pokemonrestocks"].first == 1
    assert card["bluesky:nowinstockus"].median_lag_s == 240
