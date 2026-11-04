"""Bluesky restock posts: classification, watchlist matching, and ingestion."""

from __future__ import annotations

import datetime as dt
import json

import pytest

from radar import matching, sources, watchlist
from radar.social import bluesky, parse

from .conftest import NOW, load_text

POSTS = {post["rkey"]: post for post in json.loads(load_text("bluesky_posts.json"))}
WATCH = watchlist.load()
SET_KEYS = ["30th celebration", "ascended heroes", "prismatic evolutions", "destined rivals", "delta reign"]


def parsed(rkey: str) -> parse.ParsedPost:
    return parse.parse_post(POSTS[rkey]["record"], set_keys=SET_KEYS)


# ---------------------------------------------------------------------------
# Signal, retailer, relevance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rkey", "signal", "retailer"),
    [
        ("3mw7nghtmvc2z", "drawing_open", "Walmart"),
        ("3mvsewzwyac22", "invites", "Amazon"),
        ("3mvpvcd3omc2j", "queue", "Costco"),
        ("3mvpy2bbxw22n", "cancelled", "Costco"),
        ("3mw2wydw5vk2d", "drawing_scheduled", "Walmart"),
        ("3mvpzzfibkk27", "drawing_results", "Walmart"),
        ("3mw7dnve36g2u", "in_stock", "Sam's Club"),
        ("3mw2qcvl6x722", "preorder", "Amazon"),
    ],
)
def test_signal_and_retailer(rkey: str, signal: str, retailer: str):
    post = parsed(rkey)
    assert post.signal == signal
    assert post.retailer == retailer


def test_last_call_to_enter_counts_as_an_open_drawing():
    record = {"text": "15 Minutes Left to Enter 30th Celebration Drawings at Walmart!"}
    assert parse.parse_post(record, set_keys=SET_KEYS).signal == "drawing_open"


def test_tcg_relevance_excludes_plush_and_sneakers_and_consoles():
    assert parsed("3mw7nghtmvc2z").is_tcg
    assert parsed("3mvpvcd3omc2j").is_tcg
    assert not parsed("3mw3dfsoois27").is_tcg  # Adidas sneaker collection
    assert not parsed("3mvq3lbp22s2p").is_tcg  # plush
    assert not parsed("3mw7dnve36g2u").is_tcg  # PS5


def test_nowinstock_structured_posts_yield_product_and_price():
    post = parsed("3mw7dnve36g2u")
    assert post.product_text.startswith("Console: Digital Slim 825GB")
    assert post.price == 649.00
    assert post.url and post.url.startswith("https://nowinstock.net/")


def test_nowinstock_pokemon_post_is_tcg_in_stock():
    # Synthetic, in NowInStock's observed format, for a Pokémon tracker item.
    record = {
        "text": "#ad #pokemon\n\n04:51 - Pokémon Cards: 30th Celebration Elite Trainer Box now available In Stock "
        "here at Target:\n https://nowinstock.net/getw99999/",
        "createdAt": "2026-09-25T08:51:10Z",
    }
    post = parse.parse_post(record, set_keys=SET_KEYS)
    assert (post.signal, post.retailer, post.is_tcg) == ("in_stock", "Target", True)
    assert post.product_text == "30th Celebration Elite Trainer Box"


def test_links_come_from_facets():
    assert parsed("3mvsewzwyac22").url == "https://amzn.to/4gUCtx4"


# ---------------------------------------------------------------------------
# Watchlist matching
# ---------------------------------------------------------------------------


def test_abbreviated_etb_matches_the_watched_elite_trainer_box():
    matches = matching.watch_matches(parsed("3mvsewzwyac22").text, WATCH, SET_KEYS)
    assert matches == ["30th Celebration Elite Trainer Box"]


def test_one_post_can_match_several_watched_items():
    text = "30th Celebration ETB, Tech Stickers, Knock Out Collections & More Walmart Drawings Open Today!"
    matches = matching.watch_matches(text, WATCH, SET_KEYS)
    assert set(matches) == {"30th Celebration Elite Trainer Box", "30th Celebration Knock Out Collection"}


def test_same_product_type_from_a_different_set_does_not_match():
    matches = matching.watch_matches("Destined Rivals Booster Bundle restock at Target", WATCH, SET_KEYS)
    assert matches == ["Destined Rivals Booster Bundle"]
    assert "Prismatic Evolutions Booster Bundle" not in matches


# ---------------------------------------------------------------------------
# Jetstream messages and ingestion
# ---------------------------------------------------------------------------


def jetstream_message(rkey: str, *, time_us: int = 1_790_000_000_000_000, operation: str = "create") -> str:
    post = POSTS[rkey]
    return json.dumps(
        {
            "did": post["did"],
            "time_us": time_us,
            "kind": "commit",
            "commit": {
                "operation": operation,
                "collection": "app.bsky.feed.post",
                "rkey": rkey,
                "record": post["record"],
            },
        }
    )


def observations(connection) -> list:
    return connection.execute("SELECT * FROM observations ORDER BY id").fetchall()


def test_created_posts_become_observations_and_advance_the_cursor(connection):
    handled = bluesky.handle_message(connection, jetstream_message("3mvsewzwyac22"), watch=WATCH, now=NOW, set_keys=SET_KEYS)
    assert handled is not None
    rows = observations(connection)
    assert len(rows) == 1
    row = rows[0]
    assert row["source_id"] == "bluesky"
    assert row["external_id"] == f"at://{POSTS['3mvsewzwyac22']['did']}/app.bsky.feed.post/3mvsewzwyac22"
    assert (row["signal"], row["retailer"], row["is_tcg"]) == ("invites", "Amazon", 1)
    assert json.loads(row["watch_matches"]) == ["30th Celebration Elite Trainer Box"]
    assert bluesky.load_cursor(connection) == 1_790_000_000_000_000


def test_replayed_messages_are_ignored(connection):
    message = jetstream_message("3mvsewzwyac22")
    bluesky.handle_message(connection, message, watch=WATCH, now=NOW)
    second = bluesky.handle_message(connection, message, watch=WATCH, now=NOW + dt.timedelta(seconds=5))
    assert second is None
    assert len(observations(connection)) == 1


def test_deletes_identity_events_and_other_collections_are_ignored(connection):
    assert bluesky.handle_message(connection, jetstream_message("3mvsewzwyac22", operation="delete"), watch=WATCH, now=NOW) is None
    assert bluesky.handle_message(connection, json.dumps({"kind": "identity", "time_us": 5}), watch=WATCH, now=NOW) is None
    assert observations(connection) == []


def test_backfill_from_author_feed_uses_the_same_ids(connection):
    post = POSTS["3mvsewzwyac22"]
    feed_item = {
        "post": {
            "uri": f"at://{post['did']}/app.bsky.feed.post/3mvsewzwyac22",
            "author": {"did": post["did"]},
            "record": post["record"],
        }
    }
    inserted = bluesky.ingest_feed_items(connection, [feed_item], watch=WATCH, now=NOW)
    assert inserted == 1
    bluesky.handle_message(connection, jetstream_message("3mvsewzwyac22"), watch=WATCH, now=NOW)
    assert len(observations(connection)) == 1


def test_subscribe_url_filters_accounts_and_rewinds_the_cursor():
    url = bluesky.subscribe_url(["did:plc:a", "did:plc:b"], cursor=10_000_000)
    assert "wantedCollections=app.bsky.feed.post" in url
    assert "wantedDids=did%3Aplc%3Aa" in url and "wantedDids=did%3Aplc%3Ab" in url
    assert "cursor=5000000" in url  # rewound 5 s so a reconnect cannot skip posts


def test_stream_source_is_registered(connection):
    assert sources.get("bluesky").kind == "stream"
