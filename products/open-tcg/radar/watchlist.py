"""The founder watchlist (watchlist.toml), the radar's single input."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .catalog.classify import set_key
from .config import WATCHLIST_PATH

# Shorter set keys (e.g. "151") would match unrelated item names.
MIN_SET_KEY_LENGTH = 5


@dataclass(frozen=True)
class WatchItem:
    name: str
    alert_at: float
    retailers: tuple[str, ...]
    auto_buy: bool
    nowinstock: tuple[str, ...] = ()
    keepa_asins: tuple[str, ...] = ()
    note: str = ""


def load(path: Path = WATCHLIST_PATH) -> list[WatchItem]:
    data = tomllib.loads(path.read_text())
    items = []
    for raw in data.get("item", []):
        items.append(
            WatchItem(
                name=raw["name"],
                alert_at=float(raw["alert_at"]),
                retailers=tuple(raw.get("retailers", [])),
                auto_buy=bool(raw.get("auto_buy", False)),
                nowinstock=tuple(raw.get("nowinstock", [])),
                keepa_asins=tuple(raw.get("keepa_asins", [])),
                note=raw.get("note", ""),
            )
        )
    return items


def set_keys_for(group_names: Iterable[str], item_names: Iterable[str]) -> set[str]:
    """Set keys whose name appears inside at least one watched item's name."""
    lowered_items = [name.lower() for name in item_names]
    keys = set()
    for group_name in group_names:
        key = set_key(group_name)
        if len(key) >= MIN_SET_KEY_LENGTH and any(key in item for item in lowered_items):
            keys.add(key)
    return keys
