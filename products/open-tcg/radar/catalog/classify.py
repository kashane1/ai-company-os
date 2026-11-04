"""Classify TCGplayer products: sealed vs single, product type, retailer exclusive."""

from __future__ import annotations

import re

# Singles carry both a collector number and a rarity in extendedData; sealed
# goods carry neither. Sealed wording overrides, because a few sealed items do
# get a Rarity (usually "Promo").
_SINGLE_REQUIRED_FIELDS = ("Number", "Rarity")
_SEALED_NAME_MARKERS = (
    "booster box",
    "booster pack",
    "booster bundle",
    "booster display",
    "elite trainer box",
    "build & battle",
    "build and battle",
    "collection box",
    "premium collection",
    "poster collection",
    "illustration collection",
    "blister",
    "sleeved booster",
    "theme deck",
    "battle deck",
)

# First match wins, so more specific wording comes first.
_PRODUCT_TYPES: tuple[tuple[str, str], ...] = (
    (r"\bcase\b", "case"),
    (r"half booster box", "half_booster_box"),
    (r"elite trainer box", "etb"),
    (r"booster (box|display)", "booster_box"),
    (r"booster bundle", "booster_bundle"),
    (r"build (&|and) battle", "build_and_battle"),
    (r"blister", "blister"),
    (r"sleeved booster", "sleeved_booster"),
    (r"booster pack", "booster_pack"),
    (r"\btin\b", "tin"),
    (r"\bdeck\b", "deck"),
    (r"poster collection", "poster_collection"),
    (r"premium collection", "premium_collection"),
    (r"collection", "collection"),
    (r"\bbox\b", "box"),
)

_KNOWN_RETAILERS = {
    "target": "Target",
    "walmart": "Walmart",
    "best buy": "Best Buy",
    "gamestop": "GameStop",
    "costco": "Costco",
    "sam's club": "Sam's Club",
    "amazon": "Amazon",
    "barnes & noble": "Barnes & Noble",
}
_POKEMON_CENTER = re.compile(r"pok[eé]mon center", re.IGNORECASE)
_EXCLUSIVE = re.compile(r"\(([^()]*?)\s*exclusive\)", re.IGNORECASE)
_ERA_PREFIX = re.compile(r"^[A-Za-z0-9.]+:\s*")
_ASCII_ACCENTS = str.maketrans({"é": "e", "É": "E"})


def _extended_data(product: dict) -> dict[str, str]:
    return {
        entry.get("name"): entry.get("value")
        for entry in product.get("extendedData") or []
        if entry.get("name")
    }


def is_sealed(product: dict) -> bool:
    lowered = (product.get("name") or "").lower()
    # Code cards are digital redemption codes, not physical inventory.
    if lowered.startswith("code card"):
        return False
    if any(marker in lowered for marker in _SEALED_NAME_MARKERS):
        return True
    fields = _extended_data(product)
    return not all(fields.get(key) for key in _SINGLE_REQUIRED_FIELDS)


def product_type(name: str) -> str:
    lowered = name.lower()
    for pattern, kind in _PRODUCT_TYPES:
        if re.search(pattern, lowered):
            return kind
    return "other"


def exclusive_retailer(name: str) -> str | None:
    if _POKEMON_CENTER.search(name):
        return "Pokemon Center"
    match = _EXCLUSIVE.search(name)
    if not match or not match.group(1).strip():
        return None
    retailer = match.group(1).strip()
    return _KNOWN_RETAILERS.get(retailer.lower(), retailer)


def known_date(value: str | None) -> str | None:
    """ISO date from a tcgcsv timestamp, or None when it is a placeholder.

    Real release dates are midnight. Undated legacy groups (POP Series,
    Miscellaneous Cards & Products) carry tcgcsv's build time instead, which
    would otherwise make old products look like today's releases.
    """
    if not value:
        return None
    date, _, time = value.partition("T")
    if time and not time.startswith("00:00:00"):
        return None
    return date[:10]


def set_key(group_name: str) -> str:
    """'SV: Prismatic Evolutions' -> 'prismatic evolutions' (era prefix removed)."""
    return _ERA_PREFIX.sub("", group_name).translate(_ASCII_ACCENTS).strip().lower()
