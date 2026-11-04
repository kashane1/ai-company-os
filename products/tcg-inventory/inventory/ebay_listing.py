"""eBay titles and item specifics, generated deterministically.

Titles are built by slot priority, not by a language model. Same input, same
output, every run — which means they can be unit tested, and a bad one can be
traced to a rule rather than to a sampling temperature.

The 80-character limit is a packing problem, so tokens are ranked by search
value and the lowest-value ones degrade through an abbreviation ladder before
anything is dropped. Substituting beats truncating: "SIR" still matches what
buyers type, while a title cut mid-word matches nothing.

The priority order here is a starting hypothesis, not measured fact. The honest
version ranks tokens by lift — how much more often a token appears in *sold*
listings than in *active* ones — which needs eBay sold comps this project does
not have yet. Until then the order below encodes the convention that serious
buyers search by card name, collector number and set.

Item specifics matter at least as much as the title and are nearly free: every
one is a left-rail filter a buyer can click, and a listing missing Card Number
is invisible to anyone filtering on it. The aspect NAMES below are best-effort
and must be checked against `getItemAspectsForCategory` for category 183454
before a real listing is published — eBay renames and re-requires them.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

MAX_TITLE_LENGTH = 80

# Pokemon singles. Condition ids: 4000 ungraded, 2750 graded.
EBAY_CATEGORY_ID = "183454"
CONDITION_ID_UNGRADED = "4000"

# Trailing collector number baked into the catalog's card name, e.g.
# "Iono - 269/193" or "AZ's Tranquility - 076/086". The number is a separate
# field, so repeating it in the name wastes title characters.
_TRAILING_NUMBER = re.compile(r"\s*-\s*\d+[A-Za-z]?(/\d+)?\s*$")

# Set-code prefixes nobody searches: "SWSH07: Evolving Skies", "SV: ...".
_SET_PREFIX = re.compile(r"^(?:[A-Z]{2,5}\d*|POP Series \d+)\s*[:\-]\s*")

# Artist credits on promos: "AZ - 2015 (Patrick Martinez)". Distinct from
# treatment qualifiers like "(Full Art)", which are worth keeping.
_ARTIST_PAREN = re.compile(r"\s*\((?![^)]*(?:Art|Secret|Holo|Edition|Rare)\b)[^)]*\)\s*$")

_RARITY_FORMS = {
    "Special Illustration Rare": ("Special Illustration Rare", "SIR"),
    "Illustration Rare": ("Illustration Rare", "IR"),
    "Ultra Rare": ("Ultra Rare", "UR"),
    "Secret Rare": ("Secret Rare", "Secret"),
    "Hyper Rare": ("Hyper Rare", "Hyper"),
    "Double Rare": ("Double Rare", "RR"),
    "Shiny Holo Rare": ("Shiny Holo Rare", "Shiny Holo"),
    "Holo Rare": ("Holo Rare", "Holo"),
}

_FINISH_FORMS = {
    "Reverse Holofoil": ("Reverse Holo", "Rev Holo", "RH"),
    "Holofoil": ("Holo",),
    "1st Edition Holofoil": ("1st Edition Holo", "1st Ed Holo"),
    "Unlimited Holofoil": ("Unlimited Holo", "Unl Holo"),
    "1st Edition": ("1st Edition", "1st Ed"),
    "Unlimited": ("Unlimited", "Unl"),
    "Normal": (),
}

# eBay's ungraded Card Condition values.
_EBAY_CONDITION = {
    "NM": "Near Mint or Better",
    "LP": "Lightly Played (Excellent)",
    "MP": "Moderately Played (Very Good)",
    "HP": "Heavily Played (Poor)",
    "DMG": "Damaged",
}

_EBAY_FINISH = {
    "Holofoil": "Holo",
    "1st Edition Holofoil": "Holo",
    "Unlimited Holofoil": "Holo",
    "Reverse Holofoil": "Reverse Holo",
    "Normal": "Regular",
    "1st Edition": "Regular",
    "Unlimited": "Regular",
}


@dataclass
class _Token:
    """One title slot. `forms` runs longest to shortest; () after that is drop."""

    forms: tuple[str, ...]
    is_required: bool = False
    _index: int = field(default=0, repr=False)

    @property
    def text(self) -> str:
        return self.forms[self._index] if self._index < len(self.forms) else ""

    @property
    def can_degrade(self) -> bool:
        if self.is_required:
            return self._index < len(self.forms) - 1
        return self._index < len(self.forms)

    def degrade(self) -> None:
        self._index += 1


@dataclass(frozen=True)
class TitleResult:
    title: str
    dropped: tuple[str, ...]

    @property
    def length(self) -> int:
        return len(self.title)


def clean_card_name(name: str, card_number: str | None = None) -> str:
    """Strip the baked-in collector number and any artist credit.

    Pass `card_number` whenever it is known. A trailing "- 2015" on a World
    Championship promo and a trailing "- 050" on a modern single are the same
    shape, so pattern-matching alone strips the year off "AZ - 2015". Matching
    against the real number removes the guess.
    """
    cleaned = _ARTIST_PAREN.sub("", name).strip()

    if card_number:
        suffix = f" - {card_number}"
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    else:
        cleaned = _TRAILING_NUMBER.sub("", cleaned)

    return cleaned.strip()


def clean_set_name(set_name: str) -> str:
    """Drop set-code prefixes buyers never type."""
    return _SET_PREFIX.sub("", set_name).strip()


def character_from(card_name: str, card_number: str | None = None) -> str:
    """The Pokemon itself, without treatment qualifiers — for the aspect."""
    base = clean_card_name(card_name, card_number)
    base = re.sub(r"\s*\([^)]*\)\s*$", "", base)
    # Anything still trailing after a dash is a year or era label, not a name.
    base = re.sub(r"\s+-\s+\d{4}$", "", base)
    # "Charizard ex", "Umbreon VMAX" -> "Charizard", "Umbreon"
    base = re.sub(r"\s+(ex|EX|GX|V|VMAX|VSTAR|BREAK|LV\.X)$", "", base)
    return base.strip()


def build_title(
    card: sqlite3.Row | dict, condition_code: str = "NM", *, include_condition: bool = True
) -> TitleResult:
    """Pack the highest-value tokens into 80 characters.

    Priority, highest first: card name, collector number, set, rarity, the word
    "Pokemon", finish, condition. Condition degrades first because it is
    already an item specific and buyers filter on it there.
    """
    name = clean_card_name(card["card_name"], card["card_number"])
    set_name = clean_set_name(card["set_name"])
    rarity = card["rarity"] or ""
    sub_type = card["sub_type"] or "Normal"
    abbreviation = (card["set_abbreviation"] or "").strip()

    set_forms = (set_name, abbreviation) if abbreviation and abbreviation != set_name else (set_name,)

    tokens = [
        _Token((name,), is_required=True),
        _Token((card["card_number"] or "",)),
        _Token(set_forms, is_required=True),
        _Token(_RARITY_FORMS.get(rarity, (rarity,) if rarity else ())),
        _Token(("Pokemon",)),
        _Token(_FINISH_FORMS.get(sub_type, (sub_type,))),
    ]
    if include_condition:
        tokens.append(_Token((condition_code,)))

    def render() -> str:
        # A token whose words are already in the title buys no extra search
        # coverage and costs characters — "Promo Promo" when a promo set's
        # rarity is also "Promo".
        parts: list[str] = []
        seen_words: set[str] = set()
        for token in tokens:
            text = token.text
            if not text:
                continue
            words = {word.casefold() for word in text.split()}
            if words and words <= seen_words:
                continue
            seen_words |= words
            parts.append(text)
        return " ".join(parts)

    dropped: list[str] = []
    # Degrade from the lowest-priority token upward until it fits.
    while len(render()) > MAX_TITLE_LENGTH:
        for token in reversed(tokens):
            if token.can_degrade:
                before = token.text
                token.degrade()
                if not token.text and before:
                    dropped.append(before)
                break
        else:
            break  # nothing left to give; required tokens alone are too long

    title = render()
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH].rstrip()

    return TitleResult(title=title, dropped=tuple(dropped))


def build_aspects(card: sqlite3.Row | dict, condition_code: str = "NM") -> dict[str, str]:
    """Item specifics for the listing.

    Every value here comes straight from the catalog — this is mechanical
    mapping, no judgement, and it is the highest-return work in the whole
    listing pipeline because each aspect is a filter buyers actually click.
    """
    sub_type = card["sub_type"] or "Normal"
    released = card["released_on"] or ""

    aspects = {
        "Game": "Pokémon TCG",
        "Set": clean_set_name(card["set_name"]),
        "Card Number": card["card_number"] or "",
        "Character": character_from(card["card_name"], card["card_number"]),
        "Card Name": clean_card_name(card["card_name"], card["card_number"]),
        "Rarity": card["rarity"] or "",
        "Card Condition": _EBAY_CONDITION.get(condition_code, "Near Mint or Better"),
        "Finish": _EBAY_FINISH.get(sub_type, "Regular"),
        "Language": "English",
        "Graded": "No",
        "Manufacturer": "The Pokémon Company",
    }

    if released[:4].isdigit():
        aspects["Year Manufactured"] = released[:4]

    # These exist in the catalog for most modern cards and map straight across.
    for column, aspect in (
        ("hp", "HP"),
        ("stage", "Stage"),
        ("card_type", "Energy Type"),
    ):
        try:
            value = card[column]
        except (IndexError, KeyError):
            value = None
        if value:
            aspects[aspect] = str(value)

    features = []
    if "1st Edition" in sub_type:
        features.append("1st Edition")
    if "Holo" in sub_type:
        features.append("Holo")
    if features:
        aspects["Features"] = ", ".join(features)

    return {key: value for key, value in aspects.items() if value}


def build_description(card: sqlite3.Row | dict, condition_code: str = "NM") -> str:
    """A short, factual description.

    Descriptions barely affect search, and overstating condition is how you
    collect not-as-described cases, so this stays plain and says only what the
    catalog knows.
    """
    name = clean_card_name(card["card_name"], card["card_number"])
    set_name = clean_set_name(card["set_name"])
    condition = _EBAY_CONDITION.get(condition_code, condition_code)
    finish = _EBAY_FINISH.get(card["sub_type"] or "Normal", "Regular")

    return (
        f"{name} — {set_name} {card['card_number'] or ''}\n"
        f"Rarity: {card['rarity'] or 'n/a'}\n"
        f"Finish: {finish}\n"
        f"Condition: {condition}\n\n"
        "Card pictured is the card you will receive. Shipped in a penny sleeve "
        "and top loader inside a rigid mailer. Ships within one business day."
    ).strip()
