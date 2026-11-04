"""Match free text (posts, alert emails) to watchlist items.

An item matches when its full normalized name appears in the text, or when
its set name and the rest of its name (the product part) both appear. The
second rule catches posts that list several products of one set, such as
"30th Celebration ETB, Tech Stickers, Knock Out Collections".
"""

from __future__ import annotations

import re
from typing import Iterable

from .watchlist import WatchItem

_ABBREVIATIONS = {
    "etb": "elite trainer box",
    "etbs": "elite trainer boxes",
    "spc": "super premium collection",
    "upc": "ultra premium collection",
}
_NON_WORD = re.compile(r"[^a-z0-9 ]+")
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    lowered = text.lower().replace("é", "e").replace("&", " and ").replace("-", " ")
    words = _SPACES.sub(" ", _NON_WORD.sub(" ", lowered)).split()
    return " ".join(_ABBREVIATIONS.get(word, word) for word in words)


def _contains(haystack: str, needle: str) -> bool:
    # Word-boundary containment; a trailing "s" (plurals) is allowed.
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}s?(?![a-z0-9])", haystack) is not None


def watch_matches(text: str, items: Iterable[WatchItem], set_keys: Iterable[str]) -> list[str]:
    haystack = normalize(text)
    keys = sorted({normalize(key) for key in set_keys if key}, key=len, reverse=True)
    matches = []
    for item in items:
        name = normalize(item.name)
        if _contains(haystack, name):
            matches.append(item.name)
            continue
        set_part = next((key for key in keys if name.startswith(key + " ")), None)
        if not set_part or not _contains(haystack, set_part):
            continue
        product_part = name[len(set_part):].strip()
        if product_part and _contains(haystack, product_part):
            matches.append(item.name)
    return matches
