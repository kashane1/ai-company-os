"""Bluesky restock accounts via Jetstream, with an author-feed backfill.

Jetstream is Bluesky's free, unauthenticated JSON firehose. The subscription
is filtered to a few restock-alert accounts, and the last event time is
saved, so a restart resumes where it stopped. On startup the public
author-feed API fills any gap longer than Jetstream's replay window. Both
paths key posts by their at:// URI, so a post is stored once.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
import time
from typing import Callable, Iterable
from urllib.parse import urlencode

from .. import matching, sources
from ..catalog.classify import set_key
from ..config import BLUESKY_ACCOUNTS, BLUESKY_PUBLIC_API, JETSTREAM_URL
from ..db import iso
from ..http import tls_context
from ..watchlist import WatchItem
from . import parse

SOURCE_ID = "bluesky"
POST_COLLECTION = "app.bsky.feed.post"
# Rewind on reconnect so an event in flight when the socket dropped is replayed.
CURSOR_REWIND_US = 5_000_000
MAX_BACKOFF_S = 60



def post_uri(did: str, rkey: str) -> str:
    return f"at://{did}/{POST_COLLECTION}/{rkey}"


def subscribe_url(dids: Iterable[str], cursor: int | None = None) -> str:
    params = [("wantedCollections", POST_COLLECTION)] + [("wantedDids", did) for did in dids]
    if cursor:
        params.append(("cursor", str(max(cursor - CURSOR_REWIND_US, 0))))
    return f"{JETSTREAM_URL}?{urlencode(params)}"


def load_cursor(connection: sqlite3.Connection) -> int | None:
    row = connection.execute("SELECT cursor FROM stream_cursors WHERE source_id = ?", (SOURCE_ID,)).fetchone()
    return row["cursor"] if row else None


def _save_cursor(connection: sqlite3.Connection, cursor: int, now: dt.datetime) -> None:
    connection.execute(
        """
        INSERT INTO stream_cursors (source_id, cursor, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET cursor = MAX(cursor, excluded.cursor), updated_at = excluded.updated_at
        """,
        (SOURCE_ID, cursor, iso(now)),
    )


def catalog_set_keys(connection: sqlite3.Connection) -> list[str]:
    names = [row["name"] for row in connection.execute("SELECT name FROM catalog_groups")]
    return sorted({key for key in map(set_key, names) if len(key) >= 5})


def _store(
    connection: sqlite3.Connection,
    *,
    did: str,
    uri: str,
    record: dict,
    watch: Iterable[WatchItem],
    set_keys: Iterable[str],
    now: dt.datetime,
) -> int | None:
    keys = list(set_keys)
    post = parse.parse_post(record, set_keys=keys)
    matches = matching.watch_matches(post.text, watch, keys) if post.is_tcg else []
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO observations
            (source_id, external_id, author, text, signal, retailer, product_text, price, url,
             is_tcg, watch_matches, source_time, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            SOURCE_ID, uri, did, post.text, post.signal, post.retailer, post.product_text, post.price,
            post.url, int(post.is_tcg), json.dumps(matches), post.created_at, iso(now),
        ),
    )
    return cursor.lastrowid if cursor.rowcount else None


def handle_message(
    connection: sqlite3.Connection,
    raw: str,
    *,
    watch: Iterable[WatchItem],
    now: dt.datetime,
    set_keys: Iterable[str] | None = None,
) -> int | None:
    """Store one Jetstream event; returns the new observation id, if any."""
    message = json.loads(raw)
    time_us = message.get("time_us")
    commit = message.get("commit") or {}
    observation_id = None
    if (
        message.get("kind") == "commit"
        and commit.get("operation") == "create"
        and commit.get("collection") == POST_COLLECTION
        and commit.get("record")
    ):
        observation_id = _store(
            connection,
            did=message["did"],
            uri=post_uri(message["did"], commit["rkey"]),
            record=commit["record"],
            watch=watch,
            set_keys=catalog_set_keys(connection) if set_keys is None else set_keys,
            now=now,
        )
    if time_us:
        _save_cursor(connection, int(time_us), now)
    connection.commit()
    return observation_id


def ingest_feed_items(
    connection: sqlite3.Connection,
    items: Iterable[dict],
    *,
    watch: Iterable[WatchItem],
    now: dt.datetime,
    set_keys: Iterable[str] | None = None,
) -> int:
    """Store posts from app.bsky.feed.getAuthorFeed; returns how many were new."""
    keys = catalog_set_keys(connection) if set_keys is None else list(set_keys)
    watch = list(watch)
    inserted = 0
    for item in items:
        post = item.get("post") or {}
        if item.get("reason") or not post.get("record"):  # skip reposts
            continue
        did = (post.get("author") or {}).get("did", "")
        inserted += _store(
            connection, did=did, uri=post["uri"], record=post["record"], watch=watch, set_keys=keys, now=now
        ) is not None
    connection.commit()
    return inserted


def backfill(connection: sqlite3.Connection, client, *, watch: Iterable[WatchItem], now: dt.datetime, limit: int = 30) -> int:
    watch = list(watch)
    inserted = 0
    for handle in BLUESKY_ACCOUNTS:
        response = client.get(
            f"{BLUESKY_PUBLIC_API}/app.bsky.feed.getAuthorFeed",
            params={"actor": handle, "limit": limit, "filter": "posts_no_replies"},
        )
        response.raise_for_status()
        inserted += ingest_feed_items(connection, response.json().get("feed") or [], watch=watch, now=now)
    return inserted


def run_stream(
    connection: sqlite3.Connection,
    *,
    watch: Iterable[WatchItem],
    on_observation: Callable[[int], None] | None = None,
    clock: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.timezone.utc),
) -> None:
    """Follow Jetstream forever, reconnecting with capped exponential backoff."""
    from websockets.sync.client import connect  # imported here: only the daemon needs it

    watch = list(watch)
    heartbeat_s = sources.get(SOURCE_ID).cadence_s
    backoff = 1
    while True:
        try:
            url = subscribe_url(BLUESKY_ACCOUNTS.values(), load_cursor(connection))
            with connect(url, open_timeout=15, ssl=tls_context()) as socket:
                sources.record_run(connection, SOURCE_ID, ok=True, now=clock())
                last_beat = time.monotonic()
                backoff = 1
                while True:
                    try:
                        raw = socket.recv(timeout=heartbeat_s)
                    except TimeoutError:
                        raw = None
                    if raw is not None:
                        observation_id = handle_message(connection, raw, watch=watch, now=clock())
                        if observation_id and on_observation:
                            on_observation(observation_id)
                    if time.monotonic() - last_beat >= heartbeat_s:
                        sources.record_run(connection, SOURCE_ID, ok=True, now=clock())
                        last_beat = time.monotonic()
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # network drops are expected; record and reconnect
            sources.record_run(connection, SOURCE_ID, ok=False, error=f"{type(exc).__name__}: {exc}", now=clock())
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_S)
