"""Southern Hobby's public Pokémon release list (distributor order-due dates).

robots.txt allows /ccg-s/. The listing is a plain HTML table with columns
Product Name, Item #, Release Date, Order Due. Prices need a login and are
never read.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import sqlite3
from dataclasses import dataclass
from typing import Callable

from .. import sources
from ..config import SOUTHERN_HOBBY_MAX_PAGES, SOUTHERN_HOBBY_URL
from ..db import iso, record_event

SOURCE_ID = "southern_hobby"

_ROW = re.compile(r'<tr class="productListing">(.*?)</tr>', re.S)
_CELL = re.compile(r'<td[^>]*class="productListing-data"[^>]*>(.*?)</td>', re.S)
_LINK = re.compile(r'<a href="([^"]+)">(.*?)</a>', re.S)
_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class DistributorItem:
    item_no: str
    name: str
    url: str | None
    release_on: str | None
    order_due_on: str | None


def _text(fragment: str) -> str:
    return html.unescape(_TAG.sub("", fragment)).replace("\xa0", " ").strip()


def _us_date(value: str) -> str | None:
    try:
        return dt.datetime.strptime(value.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None


def parse_listing(page_html: str) -> list[DistributorItem]:
    items = []
    for row in _ROW.findall(page_html):
        cells = _CELL.findall(row)
        if len(cells) < 5:
            continue
        link = _LINK.search(cells[1])
        item_no = _text(cells[2])
        if not link or not item_no:
            continue
        items.append(
            DistributorItem(
                item_no=item_no,
                name=_text(link.group(2)),
                url=link.group(1),
                release_on=_us_date(_text(cells[3])),
                order_due_on=_us_date(_text(cells[4])),
            )
        )
    return items


def fetch_page_with(client) -> Callable[[int], str]:
    def fetch_page(page: int) -> str:
        response = client.get(SOUTHERN_HOBBY_URL, params={"page": page} if page > 1 else None)
        response.raise_for_status()
        return response.text

    return fetch_page


def _date_change(
    connection: sqlite3.Connection,
    *,
    kind: str,
    item: DistributorItem,
    old: str | None,
    new: str | None,
    now: dt.datetime,
) -> bool:
    if old == new:
        return False
    return record_event(
        connection,
        source_id=SOURCE_ID,
        kind=kind,
        subject_key=item.item_no,
        subject_text=item.name,
        value=f"{old} -> {new}",
        now=now,
    )


def sync(
    connection: sqlite3.Connection,
    *,
    fetch_page: Callable[[int], str],
    now: dt.datetime,
    max_pages: int = SOUTHERN_HOBBY_MAX_PAGES,
) -> int:
    """Store every listed item; returns the number of new events."""
    emit = sources.has_succeeded(connection, SOURCE_ID)
    emitted = 0
    for page in range(1, max_pages + 1):
        items = parse_listing(fetch_page(page))
        if not items:
            break
        for item in items:
            existing = connection.execute(
                "SELECT release_on, order_due_on FROM distributor_items WHERE source_id = ? AND item_key = ?",
                (SOURCE_ID, item.item_no),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO distributor_items
                    (source_id, item_key, name, release_on, order_due_on, url, first_seen_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, item_key) DO UPDATE SET
                    name = excluded.name,
                    release_on = excluded.release_on,
                    order_due_on = excluded.order_due_on,
                    url = excluded.url,
                    updated_at = excluded.updated_at
                """,
                (SOURCE_ID, item.item_no, item.name, item.release_on, item.order_due_on, item.url, iso(now), iso(now)),
            )
            if not emit:
                continue
            if existing is None:
                emitted += record_event(
                    connection,
                    source_id=SOURCE_ID,
                    kind="distributor_listed",
                    subject_key=item.item_no,
                    subject_text=item.name,
                    now=now,
                )
                continue
            emitted += _date_change(
                connection, kind="release_date_changed", item=item,
                old=existing["release_on"], new=item.release_on, now=now,
            )
            emitted += _date_change(
                connection, kind="order_due_changed", item=item,
                old=existing["order_due_on"], new=item.order_due_on, now=now,
            )
    connection.commit()
    return emitted
