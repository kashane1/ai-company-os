"""Match store listing titles to the reference sealed catalog.

Conservative by design: a listing is `exact` only when its set, form, Pokémon
Center flag and variant resolve to exactly one catalog product. Everything
else is `ambiguous`, `unmatched` or `excluded`, with a reason. Titles that
name no set ("Mega Greninja ex Premium Collection"), or only an era
("Mega Evolution Elite Trainer Box"), must also leave no unexplained words,
so a set the catalog lacks is never mistaken for one it has.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass

from ..catalog import classify

POKEMON = re.compile(r"pok[eé]mon", re.IGNORECASE)

_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("ja", r"\bjapanese\b|\bjapan\b|\bjpn?\b|\(jp\)|\(j\)|日本"),
    ("ko", r"\bkorean\b|\bkor\b"),
    # Slim packs, "Collect 151" volumes and Gem Packs are Simplified Chinese products.
    ("zh", r"\bchinese\b|\bsimplified\b|\btraditional chinese\b|\bs-chinese\b|\bslim booster\b|\bcollect 151\b|\bgem pack\b"),
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
    ("graded", r"\b(psa|bgs|cgc|sgc|tag)\s?\d|\bgraded\b|\bslab\b|\bpsa\b.*\bgem mt\b|\bgrade \d+\b"),
    ("code_card", r"\bcode cards?\b|\bonline code\b|\bptcgl code\b"),
    ("empty_or_opened", r"\bempty\b|\bopened\b|\bno packs\b|\bbox only\b"),
    ("repack", r"\brepacks?\b|\bmystery\b|\bgrab bag\b|\blottery\b|\bbreak\b|\bspot\b|\blivestream\b"),
    (
        "single_card",
        r"\b\d{1,3}/(\d{2,3}|null)\b|#\s?\d{1,3}\b|\bholo\b|\bholofoil\b|\breverse\b|\bfull art\b"
        # "Near Mint" is left out: some stores label sealed variants "Near Mint / English / New".
        r"|\b(lightly played|moderately played|heavily played)\b",
    ),
    (
        "accessory",
        r"\bsleeves?\b|\bbinder\b|\bplaymat\b|\bdeck box\b|\bportfolio\b|\btoploaders?\b"
        r"|\bacrylic\b|\bmagnetic\b|\bprotectors?\b|\bdisplay case\b|\bplush\b",
    ),
)

# Release dates ("10/30/2026") look like card numbers; drop them first.
_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")

# A count other than one makes the price incomparable, unless the chosen
# product is itself a multiple: a set, case or display.
_QUANTITY = re.compile(r"\bx\s?(?:[2-9]|\d{2,})\b|\b(?:[2-9]|\d{2,})\s?x\b|\blot\b|\bcase of\b|\bbundle of \d|\bset of \d")
_MULTIPLE_PRODUCT = re.compile(r"\bset of\b|\bcase\b|\bdisplay\b")

# Era names appear alongside the real set name; alone they name the era's base set.
_ERA_KEYS = frozenset({"mega evolution", "scarlet & violet", "sword & shield", "sun & moon", "sm", "xy", "black & white"})
_GENERIC_ALIASES = frozenset({"base set", "promo cards", "promos"})

_ABBREVIATIONS = (
    (re.compile(r"\betbs?\b"), "elite trainer box"),
    (re.compile(r"\bb\s?&\s?b\b|\bbuild and battle\b"), "build & battle"),
    (re.compile(r"\bbooster displays?\b"), "booster box"),
    (re.compile(r"\bpc\b(?=.*elite trainer box)"), "pokemon center"),
    (re.compile(r"\bscarlet and violet\b"), "scarlet & violet"),
    (re.compile(r"\bmega evolutions\b"), "mega evolution"),
    (re.compile(r"\bpokeball\b"), "poke ball"),
    (re.compile(r"\bhalf-booster\b"), "half booster"),
    (re.compile(r"\bbooster packs? \(sleeved\)"), "sleeved booster pack"),
    (re.compile(r"\b(\d)[- ]booster blister\b"), r"\1 pack blister"),
    (re.compile(r"\bsword and shield\b"), "sword & shield"),
    (re.compile(r"\bsuper premium\b"), "super-premium"),
    (re.compile(r"\bultra premium\b"), "ultra-premium"),
)
_PLURALS = (
    (re.compile(r"\bboxes\b"), "box"),
    (re.compile(r"\bbundles\b"), "bundle"),
    (re.compile(r"\btins\b"), "tin"),
    (re.compile(r"\bblisters\b"), "blister"),
    (re.compile(r"\bdecks\b"), "deck"),
    (re.compile(r"\bcollections\b"), "collection"),
    (re.compile(r"\bdisplays\b"), "display"),
    (re.compile(r"\bcases\b"), "case"),
)
# What a product contains ("with 6 booster packs", "(36 packs)") says nothing
# about its form; it's dropped before the form is read.
_CONTENTS = re.compile(
    r"\((?:[^)]*\b\d+\s*(?:booster\s*)?packs?\b[^)]*)\)|\b(?:with|includes?|including|contains?)\b.*$"
    r"|\(\s*from\b[^)]*\)"
    r"|\b\d+\s*(?:booster\s*)?packs?\b(?!\s*blister)"
)
# "(Order 6 for Sealed Case)" and "(FREE Double Box Shipping)" describe the
# offer, not the product; they're dropped before anything is read.
_BULK_NOTE = re.compile(r"\((?:order|buy) \d+[^)]*\)|\([^)]*\bshipping\b[^)]*\)?|\bfree\b[^()]*\bshipping\b")
# Several loose packs ("36 Loose Packs", "(36 Packs)") of a single-pack product.
_PACK_COUNT = re.compile(r"\b(?:[2-9]|\d{2,})\s+(?:[a-z]+\s+){0,3}packs?\b(?!\s+blister)")
_SINGLE_PACK_FORMS = frozenset({"booster_pack", "sleeved_booster"})

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP_TOKENS = frozenset({"pokemon", "tcg", "the", "and", "of", "english", "sealed", "new", "card", "cards", "game"})
# Words that may appear in any title without naming a product.
_GENERIC_TOKENS = _STOP_TOKENS | frozenset(
    {
        "a", "an", "for", "in", "on", "to", "w", "with", "by", "edition", "version", "official", "authentic",
        "factory", "brand", "retail", "product", "products", "trading", "tcgs", "ccg", "us", "usa", "en", "eng",
        "preorder", "pre", "order", "orders", "release", "releases", "date", "live", "drop", "in", "stock",
        "limit", "ships", "shipping", "free", "random", "art", "artwork", "varies", "style", "styles", "assorted",
        "exclusive", "exclusives", "center", "single", "one", "pack", "packs", "booster", "boosters", "box",
        "display", "case", "set", "sets", "series", "collection", "unopened", "default", "title", "x1", "1x",
        "ex", "v", "vmax", "vstar", "gx", "mega", "evolution", "scarlet", "violet", "sword", "shield", "sun",
        "moon", "expansion", "expansions", "special", "premium", "elite", "trainer", "tin", "tins", "mini",
        "blister", "bundle", "sleeved", "build", "battle", "deck", "kit", "anniversary", "celebration",
        "base", "miscellaneous", "mcap", "xy", "sm", "swsh", "sv", "me", "bw", "regular", "standard", "loose",
    }
)
# Set and promo codes ("ME05", "SV8.5" -> "sv8", "SVP011", "SWSH07").
# Plain numbers are explained too, except years: "Poke Ball Tins (2025)" isn't the 2024 tin.
_SET_CODE = re.compile(r"^(me|sv|svp|swsh|swshp|sm|smp|xy|xyp|bw|bwp|m)\d+[a-z]{0,2}$|^(?!(?:19|20)\d\d$)\d+$")


@dataclass(frozen=True)
class MatchResult:
    language: str
    status: str  # exact | ambiguous | unmatched | excluded (| confirmed, from a decision)
    reason: str | None
    catalog_product_id: int | None = None


@dataclass(frozen=True)
class CatalogProduct:
    product_id: int
    group_id: int
    name: str
    product_type: str
    exclusive_retailer: str | None
    tokens: frozenset[str]  # all name tokens
    extra_tokens: frozenset[str]  # what distinguishes it within its set and form
    distinct_tokens: frozenset[str]  # what distinguishes it across all sets, for set-less titles


def fold(text: str) -> str:
    """Lowercase, accents removed, dashes, colons and pipes turned into spaces."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    # "/" stays: it marks card numbers ("069/185").
    return re.sub(r"\s+", " ", re.sub(r"\s+-\s+|[‐-―:|\\–—]+", " ", stripped.lower())).strip()


def _normalize(text: str) -> str:
    for pattern, replacement in _ABBREVIATIONS + _PLURALS:
        text = pattern.sub(replacement, text)
    return text


# Kept for callers that only need abbreviations expanded.
_expand = _normalize


def _stem(token: str) -> str:
    """Plural and possessive endings dropped, the same way on both sides."""
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(text: str) -> set[str]:
    text = re.sub(r"'s\b|’s\b", "", text)
    return {_stem(token) for token in _TOKEN.findall(text)} - _STOP_TOKENS


_GENERIC_TOKENS = frozenset(_stem(token) for token in _GENERIC_TOKENS)


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


def _set_aliases(key: str) -> list[str]:
    """'scarlet & violet 151' -> ['scarlet & violet 151', '151']."""
    aliases = [key]
    for era in _ERA_KEYS:
        if key.startswith(era + " "):
            rest = key[len(era) + 1 :].strip()
            if rest and rest not in _GENERIC_ALIASES and (len(rest) >= 5 or rest.isdigit()):
                aliases.append(rest)
    return aliases


class Catalog:
    """Set keys and sealed products from the reference catalog (`ref_*` tables)."""

    def __init__(
        self,
        keys: dict[str, set[int]],
        products: dict[int, list[CatalogProduct]],
        era_base: dict[str, int] | None = None,
        abbreviations: frozenset[str] = frozenset(),
    ):
        self.keys = keys  # set key or alias -> group ids
        self.products = products  # group id -> products
        self.era_base = era_base or {}  # era key -> its base set's group id
        # Set abbreviations ("DRI", "PGO") stores tag titles with; they explain words.
        self.abbreviations = abbreviations
        self.by_form: dict[str, list[CatalogProduct]] = {}
        for group_products in products.values():
            for product in group_products:
                self.by_form.setdefault(product.product_type, []).append(product)

    @classmethod
    def from_rows(
        cls,
        groups: list[tuple[int, str]],
        rows: list[tuple[int, int, str, str, str | None]],
        abbreviations: list[str] = (),
    ) -> "Catalog":
        """groups: (group_id, name); rows: (product_id, group_id, name, product_type, exclusive_retailer)."""
        group_names = dict(groups)
        products: dict[int, list[CatalogProduct]] = {}
        for product_id, group_id, name, product_type, exclusive_retailer in rows:
            if group_id not in group_names:
                continue
            key = fold(classify.set_key(group_names[group_id]))
            folded = _normalize(fold(name))
            form_words = _tokens(product_type.replace("_", " ")) | _tokens(_FORM_WORDS.get(product_type, ""))
            tokens = _tokens(folded)
            products.setdefault(group_id, []).append(
                CatalogProduct(
                    product_id=product_id,
                    group_id=group_id,
                    name=name,
                    product_type=product_type,
                    exclusive_retailer=exclusive_retailer,
                    tokens=frozenset(tokens),
                    extra_tokens=frozenset(tokens - _tokens(key) - form_words - {"exclusive", "center"}),
                    distinct_tokens=frozenset(tokens - form_words - {"exclusive", "center"}),
                )
            )
        keys: dict[str, set[int]] = {}
        era_base: dict[str, int] = {}
        for group_id, name in groups:
            if group_id not in products or name == "Miscellaneous Cards & Products":
                continue
            key = fold(classify.set_key(name))
            for alias in _set_aliases(key):
                keys.setdefault(alias, set()).add(group_id)
            for era in _ERA_KEYS:
                if key in (era, f"{era} base set"):
                    era_base[era] = group_id
        abbreviation_tokens = frozenset(
            _stem(token) for abbreviation in abbreviations for token in _TOKEN.findall(fold(abbreviation or ""))
        )
        return cls(keys, products, era_base, abbreviation_tokens)

    @classmethod
    def from_db(cls, connection: sqlite3.Connection) -> "Catalog":
        group_rows = connection.execute("SELECT group_id, name, abbreviation FROM ref_groups").fetchall()
        groups = [(row["group_id"], row["name"]) for row in group_rows]
        abbreviations = [row["abbreviation"] for row in group_rows if row["abbreviation"]]
        rows = [
            (row["product_id"], row["group_id"], row["name"], row["product_type"], row["exclusive_retailer"])
            for row in connection.execute(
                "SELECT product_id, group_id, name, product_type, exclusive_retailer FROM ref_products"
            )
        ]
        return cls.from_rows(groups, rows, abbreviations)

    def set_keys_in(self, text: str) -> list[str]:
        found = [key for key in self.keys if re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", text)]
        # "30th celebration" inside "30th celebration classic collection" is the same mention.
        found = [key for key in found if not any(key != other and key in other for other in found)]
        if len(found) > 1:
            found = [key for key in found if key not in _ERA_KEYS] or found
        return found


def _is_promo_card(text: str) -> bool:
    """A loose promo card, not a sealed product that includes one."""
    if re.search(r"\belite trainer box promo\b", text):
        return True
    return bool(re.search(r"\bpromo\b", text)) and not re.search(
        r"\b(collection|blister|tin|bundle|booster|box)\b", text
    )


def _read_form(text: str) -> str:
    text = _BULK_NOTE.sub(" ", text)
    without_contents = _CONTENTS.sub(" ", text)
    form = classify.product_type(without_contents)
    return form if form != "other" else classify.product_type(text)


def _form(title_text: str, variant_title: str | None) -> str:
    """A non-default variant names the form when the product title spans
    several ("Booster Boxes & Cases" sold as "1 Sealed Booster Box")."""
    title_form = _read_form(title_text)
    if variant_title and variant_title.lower() != "default title":
        variant_form = _read_form(_normalize(fold(variant_title)))
        # A bare "Box" or "Collection" variant ("Big Box") doesn't override a specific title form.
        is_generic = variant_form in ("box", "collection") and title_form != "other"
        # "Half Booster Boxes" sold as "1 Sealed Booster Box (36 Packs)" are still half boxes.
        is_half_box = title_form == "half_booster_box" and variant_form == "booster_box"
        # A case title keeps its form unless the variant names one unit ("1 Sealed Booster Box").
        is_case_contents = title_form == "case" and not re.search(r"^\s*(1|one|single|x1|1x)\b", fold(variant_title))
        if variant_form != "other" and not is_generic and not is_half_box and not is_case_contents:
            return variant_form
    return title_form


def listing_text(title: str, variant_title: str | None) -> str:
    if variant_title and variant_title.lower() != "default title":
        return f"{title} {variant_title}"
    return title


def _filter_retail(candidates: list[CatalogProduct], text: str) -> list[CatalogProduct]:
    is_pokemon_center = "pokemon center" in text
    return [
        product
        for product in candidates
        if (product.exclusive_retailer == "Pokemon Center") == is_pokemon_center
        # Other retailer exclusives only when the title names that retailer.
        and (
            product.exclusive_retailer in (None, "Pokemon Center")
            or fold(product.exclusive_retailer) in text
        )
    ]


def _best(candidates: list[CatalogProduct], listing_tokens: set[str], attribute: str) -> tuple[CatalogProduct | None, str | None]:
    qualified = [product for product in candidates if getattr(product, attribute) <= listing_tokens]
    if not qualified:
        return None, "variant_unclear"
    best_size = max(len(getattr(product, attribute)) for product in qualified)
    best = [product for product in qualified if len(getattr(product, attribute)) == best_size]
    if len(best) > 1:
        # "... [Set of 2]" in the title picks the set over its single items.
        sets = [product for product in best if "set" in product.tokens and "set" in listing_tokens]
        if len(sets) == 1:
            return sets[0], None
        return None, "variant_unclear"
    return best[0], None


def _is_distinctive(product: CatalogProduct) -> bool:
    """Enough of a name to find a product without its set: two words, or one
    uncommon word ("Unova Poster Collection")."""
    words = product.distinct_tokens - _GENERIC_TOKENS
    return len(product.distinct_tokens) >= 2 or any(len(word) >= 5 for word in words)


def _unexplained(listing_tokens: set[str], product: CatalogProduct, set_key: str | None, catalog: Catalog) -> set[str]:
    explained = set(product.tokens) | _GENERIC_TOKENS | catalog.abbreviations
    if set_key:
        explained |= _tokens(set_key)
    return {token for token in listing_tokens - explained if not _SET_CODE.match(token)}


def match_listing(catalog: Catalog, title: str, variant_title: str | None = None) -> MatchResult:
    raw = listing_text(title, variant_title)
    text = _BULK_NOTE.sub(" ", _normalize(fold(_DATE.sub(" ", raw))))
    language = language_of(text)
    if language != "en":
        return MatchResult(language, "excluded", "non_english")
    for reason, pattern in _EXCLUSIONS:
        if re.search(pattern, text):
            return MatchResult(language, "excluded", reason)
    if _is_promo_card(text):
        return MatchResult(language, "excluded", "promo_card")

    title_text = _normalize(fold(_DATE.sub(" ", title)))
    form = _form(title_text, variant_title)
    # A case sold through a variant ("Factory Sealed Case of 24x 3-Pack
    # Blisters") must be a case of what the title sells.
    title_form = _read_form(title_text)
    case_of = title_form if form == "case" and title_form not in ("case", "other") else None
    listing_tokens = _tokens(text)
    found = catalog.set_keys_in(text)
    non_era = [key for key in found if key not in _ERA_KEYS]

    if len(non_era) > 1:
        groups = {group for key in non_era for group in catalog.keys[key]}
        if len(groups) > 1:
            return MatchResult(language, "ambiguous", "several_sets")
    if non_era:
        set_key = non_era[0]
        groups = catalog.keys[set_key]
        is_strict = False
    elif found:  # an era name only: its base set, if nothing else is said
        set_key = found[0]
        base = catalog.era_base.get(set_key)
        if base is None:
            return MatchResult(language, "ambiguous", "era_name_only")
        groups = {base}
        is_strict = True
    else:
        set_key = None
        groups = set()
        is_strict = True

    chosen: CatalogProduct | None = None
    problem: str | None = None
    if groups:
        in_set = [product for group in groups for product in catalog.products.get(group, [])]
        candidates = _filter_retail([product for product in in_set if product.product_type == form], text)
        if case_of:
            needed = _tokens(_FORM_WORDS.get(case_of, case_of.replace("_", " ")))
            candidates = [product for product in candidates if needed <= product.tokens]
        if candidates:
            chosen, problem = _best(candidates, listing_tokens, "extra_tokens")
            if chosen is not None and form == "other" and not chosen.extra_tokens:
                chosen, problem = None, "unknown_form"
        else:
            problem = "unknown_form" if form == "other" else "form_not_in_set"
    if not groups or problem in ("form_not_in_set", "unknown_form"):
        # No set named, or the named "set" has no such product ("Arceus V
        # Figure Collection" is not the 2009 Arceus set): a product whose own
        # name (two or more distinctive words) is fully in the title, and the
        # only such one. These must leave no unexplained words.
        candidates = _filter_retail(
            [product for product in catalog.by_form.get(form, []) if _is_distinctive(product)],
            text,
        )
        if any(product.distinct_tokens <= listing_tokens for product in candidates):
            chosen, problem = _best(candidates, listing_tokens, "distinct_tokens")
            if chosen is not None:
                set_key, is_strict = None, True
        elif not groups:
            problem = "unknown_form" if form == "other" else "set_not_in_catalog"
            return MatchResult(language, "unmatched", problem)
        else:
            if set_key in _ERA_KEYS:
                return MatchResult(language, "ambiguous", "era_name_only")
            return MatchResult(language, "unmatched", problem)

    if chosen is None:
        if set_key in _ERA_KEYS:
            return MatchResult(language, "ambiguous", "era_name_only")
        return MatchResult(language, "ambiguous", problem)
    if is_strict and _unexplained(listing_tokens, chosen, set_key, catalog):
        reason = "era_name_only" if set_key in _ERA_KEYS else "unexplained_words"
        return MatchResult(language, "ambiguous", reason)
    # A damaged box is real stock, but its price isn't comparable to a clean one.
    if re.search(r"\bdamaged\b", text):
        return MatchResult(language, "ambiguous", "damaged")
    is_multiple = _MULTIPLE_PRODUCT.search(fold(chosen.name))
    if _QUANTITY.search(text) and not is_multiple:
        return MatchResult(language, "ambiguous", "quantity_unclear")
    # Set names can be numbers ("151"); they aren't pack counts.
    count_text = text
    for key in found:
        count_text = count_text.replace(key, " ")
    if chosen.product_type in _SINGLE_PACK_FORMS and not is_multiple and _PACK_COUNT.search(count_text):
        return MatchResult(language, "ambiguous", "quantity_unclear")
    return MatchResult(language, "exact", None, chosen.product_id)


def candidates(catalog: Catalog, title: str, variant_title: str | None = None, limit: int = 6) -> list[CatalogProduct]:
    """Catalog products a reviewer might pick for a listing, closest first.

    Products of the listing's form in the set(s) it names, or across all sets
    when it names none, ranked by how many of their words the title shares.
    """
    text = _BULK_NOTE.sub(" ", _normalize(fold(_DATE.sub(" ", listing_text(title, variant_title)))))
    form = _form(_normalize(fold(_DATE.sub(" ", title))), variant_title)
    listing_tokens = _tokens(text)
    groups = {group for key in catalog.set_keys_in(text) for group in catalog.keys[key]}
    for key in catalog.set_keys_in(text):
        if key in catalog.era_base:
            groups.add(catalog.era_base[key])
    if groups:
        pool = [product for group in groups for product in catalog.products.get(group, [])]
        same_form = [product for product in pool if product.product_type == form]
        pool = same_form or pool
    else:
        pool = catalog.by_form.get(form, [])
    ranked = sorted(pool, key=lambda product: (-len(product.tokens & listing_tokens), len(product.tokens), product.name))
    return [product for product in ranked if product.tokens & listing_tokens][:limit]
