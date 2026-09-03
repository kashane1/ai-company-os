"""Sync the Pokemon catalog (sets, singles, finishes) from tcgcsv.com."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import httpx

from . import classify, tcgcsv
from .config import KNOWN_SUB_TYPES

# A TCGplayer "product" in category 3 is a single card only if it carries both
# a collector number and a rarity in extendedData. Sealed products (Elite
# Trainer Boxes, booster bundles, tins) carry neither. This is the cheapest
# reliable discriminator available in the feed.
_SINGLE_REQUIRED_FIELDS = ("Number", "Rarity")

# Sealed items occasionally do get a Rarity, so drop obvious sealed wording too.
_SEALED_NAME_MARKERS = (
    "booster box",
    "booster pack",
    "booster bundle",
    "elite trainer box",
    "collection box",
    "build & battle",
    "build and battle",
    "theme deck",
    "starter deck",
    "premium collection",
    "tin)",
    "blister",
    "code card",
)


@dataclass
class CatalogSyncResult:
    sets_upserted: int = 0
    cards_upserted: int = 0
    variants_upserted: int = 0
    products_skipped: int = 0


def _extended_data(product: dict) -> dict[str, str]:
    return {
        entry.get("name"): entry.get("value")
        for entry in product.get("extendedData") or []
        if entry.get("name")
    }


def is_single(product: dict) -> bool:
    """True when a TCGplayer product is an individual card, not sealed goods."""
    fields = _extended_data(product)
    if any(not fields.get(key) for key in _SINGLE_REQUIRED_FIELDS):
        return False
    lowered = (product.get("name") or "").lower()
    return not any(marker in lowered for marker in _SEALED_NAME_MARKERS)


def _upsert_sets(connection: sqlite3.Connection, groups: list[dict]) -> int:
    rows = [
        (
            int(group["groupId"]),
            group.get("name") or f"Set {group['groupId']}",
            group.get("abbreviation"),
            (group.get("publishedOn") or "")[:10] or None,
            1 if group.get("isSupplemental") else 0,
        )
        for group in groups
        if group.get("groupId") is not None
    ]
    connection.executemany(
        """
        INSERT INTO sets (group_id, name, abbreviation, released_on, is_supplemental)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(group_id) DO UPDATE SET
            name            = excluded.name,
            abbreviation    = excluded.abbreviation,
            released_on     = excluded.released_on,
            is_supplemental = excluded.is_supplemental
        """,
        rows,
    )
    return len(rows)


def _upsert_cards(connection: sqlite3.Connection, group_id: int, products: list[dict]) -> tuple[int, int]:
    card_rows = []
    skipped = 0
    for product in products:
        if not is_single(product):
            skipped += 1
            continue
        fields = _extended_data(product)
        card_type = fields.get("Card Type")
        stage = fields.get("Stage")
        hp = classify.coerce_hp(fields.get("HP"))
        name = product.get("name") or ""
        card_class, trainer_kind = classify.classify(card_type, stage, hp, name)
        card_rows.append(
            (
                int(product["productId"]),
                group_id,
                name,
                product.get("cleanName"),
                fields.get("Number"),
                fields.get("Rarity"),
                card_type,
                product.get("imageUrl"),
                product.get("url"),
                # Stored as NULL rather than 0 so "no HP reported" and "this is
                # not a Pokemon" do not look like the same thing downstream.
                hp or None,
                stage,
                card_class,
                trainer_kind,
            )
        )

    connection.executemany(
        """
        INSERT INTO cards (
            product_id, group_id, name, clean_name, number, rarity,
            card_type, image_url, tcgplayer_url, hp, stage, card_class,
            trainer_kind
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(product_id) DO UPDATE SET
            group_id      = excluded.group_id,
            name          = excluded.name,
            clean_name    = excluded.clean_name,
            number        = excluded.number,
            rarity        = excluded.rarity,
            card_type     = excluded.card_type,
            image_url     = excluded.image_url,
            tcgplayer_url = excluded.tcgplayer_url,
            hp            = excluded.hp,
            stage         = excluded.stage,
            card_class    = excluded.card_class,
            trainer_kind  = excluded.trainer_kind
        """,
        card_rows,
    )
    return len(card_rows), skipped


def ensure_variants(connection: sqlite3.Connection, pairs: set[tuple[int, str]]) -> int:
    """Create card_variants rows for (product_id, sub_type) pairs we've seen.

    Variants are discovered from the price feed rather than the catalog: the
    catalog does not state which finishes a card was actually printed in.
    """
    if not pairs:
        return 0
    connection.executemany(
        """
        INSERT INTO card_variants (product_id, sub_type)
        VALUES (?, ?)
        ON CONFLICT(product_id, sub_type) DO NOTHING
        """,
        sorted(pairs),
    )
    return len(pairs)


def variant_id_map(connection: sqlite3.Connection) -> dict[tuple[int, str], int]:
    return {
        (row["product_id"], row["sub_type"]): row["variant_id"]
        for row in connection.execute(
            "SELECT variant_id, product_id, sub_type FROM card_variants"
        )
    }


def sync_catalog(connection: sqlite3.Connection, *, progress=None) -> CatalogSyncResult:
    """Pull every Pokemon set and its singles into the local catalog."""
    result = CatalogSyncResult()
    with httpx.Client(
        base_url=tcgcsv.TCGCSV_BASE,
        timeout=tcgcsv.REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "pokemon-tcg-search/0.1 (+local screener)"},
    ) as client:
        groups = tcgcsv.fetch_groups(client)
        result.sets_upserted = _upsert_sets(connection, groups)
        connection.commit()

        for index, group in enumerate(groups, start=1):
            group_id = int(group["groupId"])
            try:
                products = tcgcsv.fetch_products(group_id, client)
            except (httpx.HTTPError, tcgcsv.TcgCsvError) as error:
                if progress:
                    progress(f"  ! set {group_id} ({group.get('name')}): {error}")
                continue

            cards, skipped = _upsert_cards(connection, group_id, products)
            result.cards_upserted += cards
            result.products_skipped += skipped
            connection.commit()

            if progress and (index % 25 == 0 or index == len(groups)):
                progress(
                    f"  catalog {index}/{len(groups)} sets · "
                    f"{result.cards_upserted:,} singles · {result.products_skipped:,} sealed skipped"
                )

    # Seed the finishes we already know exist for every card. The price feed
    # will add any exotic ones and unused rows simply never get observations.
    return result


def prune_variants_without_prices(connection: sqlite3.Connection) -> int:
    """Delete variant rows that never received a price observation."""
    cursor = connection.execute(
        """
        DELETE FROM card_variants
        WHERE variant_id NOT IN (SELECT DISTINCT variant_id FROM price_observations)
        """
    )
    connection.commit()
    return cursor.rowcount or 0


__all__ = [
    "CatalogSyncResult",
    "KNOWN_SUB_TYPES",
    "ensure_variants",
    "is_single",
    "prune_variants_without_prices",
    "sync_catalog",
    "variant_id_map",
]
