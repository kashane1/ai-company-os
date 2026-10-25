"""PokeBeach front-page news RSS: early reveals and release announcements."""

from __future__ import annotations

import datetime as dt
import re
import sqlite3
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Callable

from .. import sources
from ..config import POKEBEACH_RSS_URL
from ..db import iso, record_event

SOURCE_ID = "pokebeach_rss"

_PRODUCT_NEWS = re.compile(
    r"\b(releas\w*|reveal\w*|announc\w*|pre-?orders?|restock\w*|collections?|elite trainer|"
    r"booster\w*|bundles?|tins?|expansions?|binders?|product\w*)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NewsItem:
    item_key: str
    title: str
    link: str | None
    published_at: str | None


def is_product_news(title: str) -> bool:
    return bool(_PRODUCT_NEWS.search(title))


def _published(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(dt.timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def parse_feed(xml_text: str) -> list[NewsItem]:
    root = ElementTree.fromstring(xml_text)
    items = []
    for element in root.findall("./channel/item"):
        title = (element.findtext("title") or "").strip()
        link = (element.findtext("link") or "").strip() or None
        key = (element.findtext("guid") or link or "").strip()
        if not title or not key:
            continue
        items.append(NewsItem(key, title, link, _published(element.findtext("pubDate"))))
    return items


def fetch_feed_with(client) -> Callable[[], str]:
    def fetch_feed() -> str:
        response = client.get(POKEBEACH_RSS_URL)
        response.raise_for_status()
        return response.text

    return fetch_feed


def sync(connection: sqlite3.Connection, *, fetch_feed: Callable[[], str], now: dt.datetime) -> int:
    """Store new items; returns the number of new news events."""
    emit = sources.has_succeeded(connection, SOURCE_ID)
    emitted = 0
    for item in parse_feed(fetch_feed()):
        product_news = is_product_news(item.title)
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO news_items
                (source_id, item_key, title, link, published_at, is_product_news, first_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (SOURCE_ID, item.item_key, item.title, item.link, item.published_at, int(product_news), iso(now)),
        )
        if cursor.rowcount and emit:
            emitted += record_event(
                connection,
                source_id=SOURCE_ID,
                kind="news_posted",
                subject_key=item.item_key,
                subject_text=item.title,
                value="product" if product_news else "",
                now=now,
            )
    connection.commit()
    return emitted
