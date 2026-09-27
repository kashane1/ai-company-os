"""Notifications for watched restocks. One per episode, only while it is fresh.

The channel is a native macOS notification (phone push via ntfy is paused).
A notification fires when an episode:

- is for a watched item, or hits a retailer rule (e.g. any Costco drop naming
  a watched item or set);
- is an availability signal (in stock, pre-order, drop, queue, invites, open
  drawing) that opened within MAX_AGE;
- names no excluded term (e.g. "Pitch Black") and no known price above the
  item's alert threshold.

For rules with open_in_browser, the link is resolved first and the page opens
in Brave only if it really lands on that retailer's domain (assisted
checkout: the founder clicks Buy). Links from posts and emails are untrusted.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import subprocess
from typing import Callable, Iterable

import httpx

from . import watchlist
from .db import iso
from .http import make_client
from .matching import normalize
from .watchlist import Policy, WatchItem

MAX_AGE = dt.timedelta(minutes=15)
SIGNAL_LABELS = {
    "in_stock": "In stock",
    "preorder": "Pre-order open",
    "drop": "Drop",
    "queue": "Queue open",
    "invites": "Invites going out",
    "drawing_open": "Drawing open",
}

Sender = Callable[[str, str], None]

RETAILER_DOMAINS = {
    "Costco": ("costco.com",),
    "Target": ("target.com",),
    "Walmart": ("walmart.com",),
    "Pokemon Center": ("pokemoncenter.com",),
    "Amazon": ("amazon.com",),
    "Best Buy": ("bestbuy.com",),
    "GameStop": ("gamestop.com",),
    "Sam's Club": ("samsclub.com",),
}
BROWSER_APP = "Brave Browser"


def open_in_brave(url: str) -> None:
    subprocess.run(["open", "-a", BROWSER_APP, url], check=True, capture_output=True, timeout=10)


def resolve_url(url: str) -> str:
    """Follow redirects (short links) without rendering anything; returns the final URL."""
    with make_client() as client:
        response = client.get(url, timeout=httpx.Timeout(8.0, connect=5.0))
        return str(response.url)


def lands_on(url: str, retailer: str | None) -> bool:
    host = (httpx.URL(url).host or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in RETAILER_DOMAINS.get(retailer or "", ()))


def macos_notify(title: str, body: str) -> None:
    # Title and body are passed as arguments, never interpolated into AppleScript.
    subprocess.run(
        [
            "osascript",
            "-e", "on run argv",
            "-e", 'display notification (item 2 of argv) with title (item 1 of argv) sound name "Glass"',
            "-e", "end run",
            title,
            body,
        ],
        check=True,
        capture_output=True,
        timeout=10,
    )


def _first_observation(connection: sqlite3.Connection, episode_id: int) -> sqlite3.Row:
    return connection.execute(
        """
        SELECT o.* FROM episode_observations eo JOIN observations o ON o.id = eo.observation_id
        WHERE eo.episode_id = ? ORDER BY eo.lag_s LIMIT 1
        """,
        (episode_id,),
    ).fetchone()


def _watch_set_keys(connection: sqlite3.Connection, policy: Policy) -> list[str]:
    names = [row["name"] for row in connection.execute("SELECT name FROM catalog_groups")]
    return sorted(watchlist.set_keys_for(names, (item.name for item in policy.items)))


def _message(connection: sqlite3.Connection, episode: sqlite3.Row, label: str) -> tuple[str, str]:
    first = _first_observation(connection, episode["id"])
    title = f"{label} · {episode['retailer'] or 'unknown retailer'}"
    parts = [SIGNAL_LABELS.get(first["signal"], first["signal"])]
    if first["price"] is not None:
        parts.append(f"${first['price']:,.2f}")
    parts.append(f"via {first['source_id']}")
    body = " · ".join(parts) + f"\n{(first['product_text'] or first['text'])[:140]}"
    return title, body


def _assisted_open(url: str, retailer: str | None, *, open_url, resolve) -> str:
    try:
        final_url = resolve(url)
    except Exception:  # an unreachable short link still gets an alert
        final_url = ""
    if not final_url or not lands_on(final_url, retailer):
        return f"Link not opened: it does not land on {retailer}."
    try:
        open_url(final_url)
    except Exception:
        return "Could not open Brave."
    return "Opened in Brave."


def maybe_notify(
    connection: sqlite3.Connection,
    episode_id: int,
    *,
    now: dt.datetime,
    send: Sender = macos_notify,
    watch: Iterable[WatchItem] | None = None,
    policy: Policy | None = None,
    open_url: Callable[[str], None] = open_in_brave,
    resolve: Callable[[str], str] = resolve_url,
) -> bool:
    policy = policy or watchlist.load_policy()
    if watch is not None:
        policy = Policy(items=tuple(watch), exclude_terms=policy.exclude_terms, retailer_rules=policy.retailer_rules)
    episode = connection.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
    if episode is None or episode["family"] != "availability":
        return False
    if now - dt.datetime.fromisoformat(episode["opened_at"]) > MAX_AGE:
        return False

    first = _first_observation(connection, episode_id)
    text = normalize(f"{episode['product_text']} {first['text'] if first else ''}")
    if any(normalize(term) in text for term in policy.exclude_terms):
        return False

    rule = policy.rule_for(episode["retailer"])
    label = episode["watch_item"]
    if not label and rule and rule.match == "watch_items_or_sets":
        hit = next((key for key in _watch_set_keys(connection, policy) if normalize(key) in text), None)
        label = f"{episode['retailer']} drop · {hit.title()}" if hit else None
    if not label:
        return False

    thresholds = {item.name: item.alert_at for item in policy.items}
    prices = [
        row["price"]
        for row in connection.execute(
            "SELECT o.price FROM episode_observations eo JOIN observations o ON o.id = eo.observation_id "
            "WHERE eo.episode_id = ? AND o.price IS NOT NULL",
            (episode_id,),
        )
    ]
    limit = thresholds.get(episode["watch_item"])
    if prices and limit is not None and min(prices) > limit:
        return False

    title, body = _message(connection, episode, label)
    # Claim the dedupe key before any side effect, so a repeat never re-opens a page.
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO notifications (dedupe_key, episode_id, channel, title, body, created_at, status)
        VALUES (?, ?, 'macos', ?, ?, ?, 'sent')
        """,
        (f"episode:{episode_id}", episode_id, title, body, iso(now)),
    )
    connection.commit()
    if not cursor.rowcount:
        return False
    if rule and rule.open_in_browser and first and first["url"]:
        body += "\n" + _assisted_open(first["url"], episode["retailer"], open_url=open_url, resolve=resolve)
        connection.execute("UPDATE notifications SET body = ? WHERE dedupe_key = ?", (body, f"episode:{episode_id}"))
        connection.commit()
    try:
        send(title, body)
    except Exception as exc:  # a failed banner must not break ingestion
        connection.execute(
            "UPDATE notifications SET status = 'failed', error = ? WHERE dedupe_key = ?",
            (f"{type(exc).__name__}: {exc}"[:300], f"episode:{episode_id}"),
        )
        connection.commit()
        return False
    return True
