"""Upcoming sealed releases and recent "when" events."""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass, field

# Display order within a release day: collector staples first, distributor
# cases last.
_TYPE_ORDER = (
    "booster_box", "etb", "half_booster_box", "booster_bundle", "premium_collection",
    "poster_collection", "collection", "box", "build_and_battle", "deck", "tin", "blister",
    "sleeved_booster", "booster_pack", "other", "case",
)
_TYPE_RANK = {kind: index for index, kind in enumerate(_TYPE_ORDER)}


@dataclass(frozen=True)
class CalendarItem:
    product_id: int
    name: str
    set_name: str
    product_type: str
    exclusive_retailer: str | None
    market_price: float | None
    url: str | None


@dataclass
class CalendarDay:
    release_on: str
    items: list[CalendarItem] = field(default_factory=list)


def upcoming(connection: sqlite3.Connection, *, today: dt.date) -> list[CalendarDay]:
    rows = connection.execute(
        """
        SELECT p.product_id, p.name, p.product_type, p.exclusive_retailer, p.release_on, p.url,
               g.name AS set_name,
               (SELECT market_price FROM price_points pp
                 WHERE pp.product_id = p.product_id ORDER BY pp.day DESC LIMIT 1) AS market_price
        FROM products p JOIN catalog_groups g ON g.group_id = p.group_id
        WHERE p.release_on >= ?
        ORDER BY p.release_on, p.name
        """,
        (today.isoformat(),),
    ).fetchall()

    days: dict[str, CalendarDay] = {}
    for row in rows:
        day = days.setdefault(row["release_on"], CalendarDay(row["release_on"]))
        day.items.append(
            CalendarItem(
                product_id=row["product_id"],
                name=row["name"],
                set_name=row["set_name"],
                product_type=row["product_type"],
                exclusive_retailer=row["exclusive_retailer"],
                market_price=row["market_price"],
                url=row["url"],
            )
        )
    for day in days.values():
        day.items.sort(key=lambda item: (_TYPE_RANK.get(item.product_type, len(_TYPE_RANK)), item.name))
    return list(days.values())


def recent_events(connection: sqlite3.Connection, *, since: dt.datetime) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT * FROM calendar_events WHERE detected_at >= ? ORDER BY detected_at DESC, id DESC",
        (since.astimezone(dt.timezone.utc).isoformat(timespec="seconds"),),
    ).fetchall()


def _money(value: float | None) -> str:
    return f"${value:,.2f}" if value is not None else "no price yet"


def render(days: list[CalendarDay], *, today: dt.date) -> str:
    if not days:
        return "No upcoming sealed releases in the catalog."
    lines = [f"Upcoming sealed releases (as of {today:%b %d, %Y})", ""]
    for day in days:
        release = dt.date.fromisoformat(day.release_on)
        sets = sorted({item.set_name for item in day.items})
        lines.append(f"{release:%b %d, %Y} ({(release - today).days} days) · {', '.join(sets)} · {len(day.items)} products")
        for item in day.items:
            tags = [item.product_type.replace("_", " ")]
            if item.exclusive_retailer:
                tags.append(f"{item.exclusive_retailer} exclusive")
            tags.append(_money(item.market_price))
            lines.append(f"  • {item.name}  [{' · '.join(tags)}]")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
