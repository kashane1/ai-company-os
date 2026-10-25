"""Find each store's sealed Pokémon collections, so daily sweeps skip singles.

Collection names can't be trusted: one store files sealed product under a
handle ending "-singles-copy". So a name only nominates a candidate, and a
candidate is selected after its first page proves to be mostly sealed
Pokémon product according to the listing matcher.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..config import (
    STORE_COLLECTION_CANDIDATES_MAX,
    STORE_COLLECTION_LIST_MAX_PAGES,
    STORE_COLLECTION_MIN_SEALED_SHARE,
    STORE_COLLECTION_STRONG_SEALED_SHARE,
)
from . import match
from .shopify import COLLECTIONS_PATH, StoreReader

_POKEMON = re.compile(r"pok[eé]mon|\bptcg\b")
# Names that say the collection is not English sealed product. Checked on the
# title only, because handles are often stale copies of other collections.
_NOT_SEALED = re.compile(
    r"\bsingles?\b|\bgraded\b|\bslabs?\b|\bjapanese\b|\bjapan\b|\bkorean\b|\bchinese\b|\baccessor|\bsleeves?\b"
    r"|\bbinders?\b|\bplush\b|\bvideo games?\b|\bfigures?\b|\bpromos?\b|\bcodes?\b|\bevents?\b"
    r"|\bmodels?\b|\bmodel kits?\b|\bnanoblocks?\b|\bblind box(es)?\b|\btoys?\b|\bapparel\b|\btopps\b"
)
# Wording that suggests sealed product; candidates with it are sampled first.
_SEALED_HINT = re.compile(r"sealed|booster|elite|\betb\b|pre-?orders?|product|box|bundle|new release")


@dataclass(frozen=True)
class CollectionSample:
    handle: str
    title: str
    sampled_count: int  # Pokémon products on the first page
    sealed_count: int  # of those, listings with a recognized sealed TCG form

    @property
    def sealed_share(self) -> float:
        return self.sealed_count / self.sampled_count if self.sampled_count else 0.0

    @property
    def is_eligible(self) -> bool:
        return self.sealed_count > 0 and self.sealed_share >= STORE_COLLECTION_MIN_SEALED_SHARE

    @property
    def is_strong(self) -> bool:
        return self.sealed_count > 0 and self.sealed_share >= STORE_COLLECTION_STRONG_SEALED_SHARE


@dataclass
class CollectionCheck:
    candidate_count: int = 0
    samples: list[CollectionSample] = field(default_factory=list)
    error: str | None = None

    @property
    def selected_handles(self) -> list[str]:
        """Strongly sealed collections, or the eligible ones when none is strong."""
        strong = [sample.handle for sample in self.samples if sample.is_strong]
        return strong or [sample.handle for sample in self.samples if sample.is_eligible]


def candidates(collections: list[dict]) -> list[dict]:
    """Pokémon collections whose title doesn't rule out sealed product, most promising first."""
    found = []
    for collection in collections:
        title = match.fold(collection.get("title") or "")
        handle = (collection.get("handle") or "").lower()
        if not handle or not _POKEMON.search(f"{title} {handle}"):
            continue
        if _NOT_SEALED.search(title):
            continue
        if collection.get("products_count") == 0:
            continue
        found.append(collection)
    # Sealed wording first, then the biggest collections, which cover the most.
    return sorted(
        found,
        key=lambda c: (
            not _SEALED_HINT.search(match.fold(c.get("title") or "")),
            -(c.get("products_count") or 0),
            c["handle"],
        ),
    )


def sample(handle: str, title: str, products: list[dict], catalog: match.Catalog) -> CollectionSample:
    pokemon = [product for product in products if match.is_pokemon(product)]
    sealed = 0
    for product in pokemon:
        variants = product.get("variants") or [{}]
        result = match.match_listing(catalog, product.get("title") or "", variants[0].get("title"))
        # Model kits, toys and stickers aren't excluded, but have no TCG form.
        if result.status != "excluded" and result.reason != "unknown_form":
            sealed += 1
    return CollectionSample(handle=handle, title=title, sampled_count=len(pokemon), sealed_count=sealed)


def check(reader: StoreReader, catalog: match.Catalog) -> CollectionCheck:
    """List collections, then sample up to N candidates' first pages."""
    result = CollectionCheck()
    if not reader.robots_allows(COLLECTIONS_PATH):
        result.error = "robots.txt disallows /collections.json"
        return result
    nominated = candidates(reader.collections(max_pages=STORE_COLLECTION_LIST_MAX_PAGES))
    result.candidate_count = len(nominated)
    for collection in nominated[:STORE_COLLECTION_CANDIDATES_MAX]:
        products = reader.products_page(1, collection["handle"])
        result.samples.append(sample(collection["handle"], collection.get("title") or "", products, catalog))
    return result
