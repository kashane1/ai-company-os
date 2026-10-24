"""Match store listing titles to the tcgcsv sealed catalog.

Conservative by design: only a listing whose set, form, Pokémon Center flag
and variant all resolve to exactly one catalog product is `exact`. Everything
else is `ambiguous`, `unmatched` or `excluded`, with a reason, so the pilot can
measure how often matching works instead of guessing.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass

from ..catalog import classify

POKEMON = re.compile(r"pok[eé]mon", re.IGNORECASE)

_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("ja", r"\bjapanese\b|\bjapan\b|\bjpn?\b|\(jp\)|日本"),
    ("ko", r"\bkorean\b|\bkor\b"),
    ("zh", r"\bchinese\b|\bsimplified\b|\btraditional chinese\b|\bs-chinese\b"),
    ("th", r"\bthai\b"),
    ("id", r"\bindonesian\b"),
    ("de", r"\bgerman\b|\bdeutsch\b"),
    ("fr", r"\bfrench\b|\bfran[cç]ais\b"),
    ("es", r"\bspanish\b|\bespa[nñ]ol\b"),
    ("it", r"\bitalian\b"),
    ("pt", r"\bportuguese\b"),
)

# Checked in order; the first hit excludes the listing.
_EXCLUSIONS: tuple[tuple[str, str], ...] = (
    ("graded", r"\b(psa|bgs|cgc|sgc|tag)\s?\d|\bgraded\b|\bslab\b"),
    ("code_card", r"\bcode cards?\b|\bonline code\b|\bptcgl code\b"),
    ("empty_or_opened", r"\bempty\b|\bopened\b|\bno packs\b|\bbox only\b"),
    ("repack", r"\brepacks?\b|\bmystery\b|\bgrab bag\b|\blottery\b|\bbreak\b|\bspot\b"),
    ("single_card", r"\b\d{1,3}/\d{2,3}\b|#\s?\d{1,3}\b|\bholo\b|\breverse\b|\bfull art\b"),
    (
        "accessory",
        r"\bsleeves?\b|\bbinder\b|\bplaymat\b|\bdeck box\b|\bportfolio\b|\btoploaders?\b"
        r"|\bacrylic\b|\bmagnetic\b|\bprotector\b|\bdisplay case\b|\bplush\b",
    ),
)

# A count other than one makes the price incomparable unless the catalog
# product itself is a set ("[Set of 4]").
_QUANTITY = re.compile(r"\bx\s?(?:[2-9]|\d{2,})\b|\b(?:[2-9]|\d{2,})\s?x\b|\blot\b|\bcase of\b|\bbundle of \d|\bset of \d")

# Era names that appear in titles alongside the real set name.
_ERA_KEYS = frozenset({"mega evolution", "scarlet & violet", "sword & shield", "sun & moon"})

_ABBREVIATIONS = (
    (re.compile(r"\betbs?\b"), "elite trainer box"),
    (re.compile(r"\bb\s?&\s?b\b|\bbuild and battle\b"), "build & battle"),
    (re.compile(r"\bbooster display\b"), "booster box"),
    (re.compile(r"\bpc\b(?=.*elite trainer box)"), "pokemon center"),
)

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP_TOKENS = frozenset({"pokemon", "tcg", "the", "and", "of", "english", "sealed", "new", "card", "cards", "game"})


@dataclass(frozen=True)
class MatchResult:
    language: str
    status: str  # exact | ambiguous | unmatched | excluded
    reason: str | None
    catalog_product_id: int | None = None


@dataclass(frozen=True)
class CatalogProduct:
    product_id: int
    name: str
    product_type: str
    exclusive_retailer: str | None
    extra_tokens: frozenset[str]


def fold(text: str) -> str:
    """Lowercase, accents removed, dashes, colons and pipes turned into spaces."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    # "/" stays: it marks card numbers ("069/185").
    return re.sub(r"[‐-―:|\\]+", " ", stripped.lower()).replace("  ", " ")


def _expand(text: str) -> str:
    for pattern, replacement in _ABBREVIATIONS:
        text = pattern.sub(replacement, text)
    return text


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text)) - _STOP_TOKENS


def is_pokemon(product: dict) -> bool:
    tags = product.get("tags")
    tag_text = " ".join(tags) if isinstance(tags, list) else str(tags or "")
    haystack = " ".join(str(product.get(key) or "") for key in ("title", "vendor", "product_type"))
    return bool(POKEMON.search(haystack + " " + tag_text))


def language_of(text: str) -> str:
    for code, pattern in _LANGUAGES:
        if re.search(pattern, text):
            return code
    return "en"


class Catalog:
    """Set keys and sealed products from the radar's tcgcsv tables."""

    def __init__(self, groups: dict[str, int], products: dict[int, list[CatalogProduct]]):
        self.groups = groups  # set key -> group id
        self.products = products  # group id -> products

    @classmethod
    def from_db(cls, connection: sqlite3.Connection) -> "Catalog":
        groups: dict[str, int] = {}
        for row in connection.execute("SELECT group_id, name FROM catalog_groups"):
            if row["name"] in ("Miscellaneous Cards & Products",):
                continue
            groups[fold(classify.set_key(row["name"]))] = row["group_id"]
        products: dict[int, list[CatalogProduct]] = {}
        group_keys = {group_id: key for key, group_id in groups.items()}
        for row in connection.execute(
            "SELECT product_id, group_id, name, product_type, exclusive_retailer FROM products"
        ):
            key = group_keys.get(row["group_id"])
            if key is None:
                continue
            name = fold(row["name"])
            products.setdefault(row["group_id"], []).append(
                CatalogProduct(
                    product_id=row["product_id"],
                    name=row["name"],
                    product_type=row["product_type"],
                    exclusive_retailer=row["exclusive_retailer"],
                    extra_tokens=frozenset(_tokens(name) - _tokens(key) - _tokens(row["product_type"].replace("_", " "))
                                           - _tokens(_FORM_WORDS.get(row["product_type"], ""))
                                           - {"exclusive", "center"}),
                )
            )
        return cls(groups, products)

    def set_group(self, text: str) -> tuple[int | None, str | None]:
        """The single set named in `text`, or a reason it can't be chosen."""
        found = [key for key in self.groups if re.search(rf"\b{re.escape(key)}\b", text)]
        # "30th celebration" inside "30th celebration classic collection" is the same mention.
        found = [key for key in found if not any(key != other and key in other for other in found)]
        if len(found) > 1:
            found = [key for key in found if key not in _ERA_KEYS] or found
        if not found:
            return None, "set_not_in_catalog"
        # An era name alone ("Mega Evolution ...") may be the base set or a
        # later set the catalog doesn't hold (Phantasmal Flames), so it is
        # never enough for an exact match.
        if found[0] in _ERA_KEYS:
            return None, "era_name_only"
        if len(found) > 1:
            return None, "several_sets"
        return self.groups[found[0]], None


# Words that the product type already accounts for, so they don't count as
# variant-distinguishing tokens.
_FORM_WORDS = {
    "etb": "elite trainer box",
    "booster_box": "booster box",
    "half_booster_box": "half booster box",
    "booster_bundle": "booster bundle",
    "booster_pack": "booster pack",
    "sleeved_booster": "sleeved booster pack",
    "build_and_battle": "build battle box",
    "poster_collection": "poster collection",
    "premium_collection": "premium collection",
    "blister": "blister",
    "case": "case",
    "tin": "tin",
    "deck": "deck",
    "collection": "collection",
    "box": "box",
}


def _is_promo_card(text: str) -> bool:
    """A loose promo card, not a sealed product that includes one."""
    if re.search(r"\belite trainer box promo\b", text):
        return True
    return bool(re.search(r"\bpromo\b", text)) and not re.search(
        r"\b(collection|blister|tin|bundle|booster|box)\b", text
    )


# "(Order 6 for Sealed Case)" describes a bulk offer, not this variant's form.
_BULK_NOTE = re.compile(r"\((?:order|buy) \d+[^)]*\)")


def _form(text: str, variant_title: str | None) -> str:
    """A non-default variant names the form when the product title spans
    several ("Booster Boxes & Cases" sold as "1 Sealed Booster Box")."""
    if variant_title and variant_title.lower() != "default title":
        variant_form = classify.product_type(_BULK_NOTE.sub(" ", _expand(fold(variant_title))))
        if variant_form != "other":
            return variant_form
    return classify.product_type(_BULK_NOTE.sub(" ", text))


def _listing_text(title: str, variant_title: str | None) -> str:
    text = title
    if variant_title and variant_title.lower() != "default title":
        text = f"{title} {variant_title}"
    return text


def match_listing(catalog: Catalog, title: str, variant_title: str | None = None) -> MatchResult:
    raw = _listing_text(title, variant_title)
    text = _expand(fold(raw))
    language = language_of(text)
    if language != "en":
        return MatchResult(language, "excluded", "non_english")
    for reason, pattern in _EXCLUSIONS:
        if re.search(pattern, text):
            return MatchResult(language, "excluded", reason)
    if _is_promo_card(text):
        return MatchResult(language, "excluded", "promo_card")

    form = _form(text, variant_title)
    if form == "other":
        return MatchResult(language, "unmatched", "unknown_form")
    group_id, set_problem = catalog.set_group(text)
    if group_id is None:
        status = "unmatched" if set_problem == "set_not_in_catalog" else "ambiguous"
        return MatchResult(language, status, set_problem)

    is_pokemon_center = "pokemon center" in text
    candidates = [
        product
        for product in catalog.products.get(group_id, [])
        if product.product_type == form
        and (product.exclusive_retailer == "Pokemon Center") == is_pokemon_center
    ]
    # Other retailer exclusives only when the title names that retailer.
    candidates = [
        product
        for product in candidates
        if product.exclusive_retailer in (None, "Pokemon Center")
        or fold(product.exclusive_retailer) in text
    ]
    if not candidates:
        return MatchResult(language, "unmatched", "form_not_in_set")

    listing_tokens = _tokens(text)
    qualified = [product for product in candidates if product.extra_tokens <= listing_tokens]
    if not qualified:
        return MatchResult(language, "ambiguous", "variant_unclear")
    best_size = max(len(product.extra_tokens) for product in qualified)
    best = [product for product in qualified if len(product.extra_tokens) == best_size]
    if len(best) > 1:
        return MatchResult(language, "ambiguous", "variant_unclear")
    chosen = best[0]
    if _QUANTITY.search(text) and "set of" not in fold(chosen.name):
        return MatchResult(language, "ambiguous", "quantity_unclear")
    return MatchResult(language, "exact", None, chosen.product_id)
