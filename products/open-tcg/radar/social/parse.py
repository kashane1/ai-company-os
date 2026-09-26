"""Classify a restock-alert post: what happened, where, and whether it is TCG.

Two formats are handled. Free-form announcements (@pokemonrestocks) name a
retailer and an event such as a drawing, invites, a queue or a drop.
NowInStock's structured posts read "<category>: <product> now available
<In Stock|for Preorder> [for $X] here at <retailer>: <link>".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from ..matching import normalize

_RETAILERS: tuple[tuple[str, str], ...] = (
    ("Pokemon Center", r"pok[eé]mon\s*center|pokemoncenter\.com"),
    ("Target", r"\btarget\b"),
    ("Walmart", r"\bwalmart\b"),
    ("Amazon", r"\bamazon\b|amzn\.to"),
    ("Best Buy", r"\bbest\s*buy\b"),
    ("GameStop", r"\bgamestop\b"),
    ("Costco", r"\bcostco\b"),
    ("Sam's Club", r"\bsam'?s club\b"),
    ("TCGplayer", r"\btcgplayer\b"),
    ("Newegg", r"\bnewegg\b"),
    ("B&H Photo", r"\bb&h\b"),
)

# First match wins: specific events before generic availability wording.
_SIGNALS: tuple[tuple[str, str], ...] = (
    ("cancelled", r"\bcancel+ed\b"),
    ("drawing_results", r"\bdrawing results\b|\bresults (are )?(going out|sent)\b"),
    ("drawing", r"\bdrawings?\b"),
    ("invites", r"\binvit(e|es|ation|ations)\b"),
    ("queue", r"\bqueue\b"),
    ("preorder", r"\bpre-?orders?\b"),
    ("in_stock", r"\bin stock\b|\brestock(ed)?\b|\bnow available\b|\bavailable now\b|\blive now\b|\bup at\b"),
    ("drop", r"\bdrop(s|ped|ping)?\b"),
    ("event", r"\bevent\b"),
)
_DRAWING_OPEN = r"\blive\b|\bopen now\b|\bnow open\b|\bends in\b|\bleft to enter\b"

_TCG_STRONG = re.compile(
    r"pok[eé]mon (tcg|cards?|trading card)|\btcg\b|\betbs?\b|elite trainer|booster|blister|\btins?\b|"
    r"tech sticker|build (&|and) battle|premium collection|poster collection|knock out collection|"
    r"illustration collection|partner collection|promo cards?",
    re.IGNORECASE,
)
_NOT_TCG = re.compile(
    r"plush|sneaker|shoe|apparel|hoodie|t-shirt|merch|figure|console|playstation|switch|amiibo|monitor|gpu",
    re.IGNORECASE,
)

_URL = re.compile(r"https?://\S+")
_HASHTAG = re.compile(r"#\w+")
_NIS_TIME = re.compile(r"^\d{1,2}:\d{2}\s*-\s*")
_NIS_PRODUCT = re.compile(r"^(?P<category>[^:]+?):\s*(?P<product>.+?)\s+now available\b", re.IGNORECASE)
_NIS_RETAILER = re.compile(r"\bhere at\s+(?P<retailer>[^:\n]+?)\s*:", re.IGNORECASE)
_PRICE = re.compile(r"\$\s?(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)")


@dataclass(frozen=True)
class ParsedPost:
    text: str
    signal: str
    retailer: str | None
    product_text: str
    price: float | None
    url: str | None
    is_tcg: bool
    created_at: str | None


def _retailer(text: str) -> str | None:
    explicit = _NIS_RETAILER.search(text)
    if explicit:
        text = explicit.group("retailer")
    best: tuple[int, str] | None = None
    for name, pattern in _RETAILERS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), name)
    return best[1] if best else None


def _signal(text: str) -> str:
    lowered = text.lower()
    for name, pattern in _SIGNALS:
        if re.search(pattern, lowered):
            if name == "drawing":
                return "drawing_open" if re.search(_DRAWING_OPEN, lowered) else "drawing_scheduled"
            return name
    return "other"


def _url(record: dict, text: str) -> str | None:
    for facet in record.get("facets") or []:
        for feature in facet.get("features") or []:
            if feature.get("uri"):
                return feature["uri"]
    external = ((record.get("embed") or {}).get("external") or {}).get("uri")
    if external:
        return external
    match = _URL.search(text)
    return match.group(0) if match else None


def _clean(text: str) -> str:
    return " ".join(_HASHTAG.sub(" ", _URL.sub(" ", text)).split())


def _product_text(cleaned: str) -> str:
    structured = _NIS_PRODUCT.search(_NIS_TIME.sub("", cleaned))
    return structured.group("product").strip() if structured else cleaned


def is_tcg(text: str, set_keys: Iterable[str] = ()) -> bool:
    if _TCG_STRONG.search(text):
        return True
    normalized = normalize(text)
    mentions_set = any(normalize(key) in normalized for key in set_keys if key)
    return mentions_set and not _NOT_TCG.search(text)


def parse_post(record: dict, *, set_keys: Iterable[str] = ()) -> ParsedPost:
    text = record.get("text") or ""
    cleaned = _clean(text)
    price = _PRICE.search(text)
    return ParsedPost(
        text=text,
        signal=_signal(cleaned),
        retailer=_retailer(text),
        product_text=_product_text(cleaned),
        price=float(price.group(1).replace(",", "")) if price else None,
        url=_url(record, text),
        is_tcg=is_tcg(cleaned, set_keys),
        created_at=record.get("createdAt"),
    )
