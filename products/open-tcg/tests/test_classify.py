"""Sealed detection, product types, and retailer exclusives from TCGplayer names."""

from __future__ import annotations

import pytest

from radar.catalog import classify


def product(name: str, *, number: str | None = None, rarity: str | None = None) -> dict:
    extended = []
    if number:
        extended.append({"name": "Number", "value": number})
    if rarity:
        extended.append({"name": "Rarity", "value": rarity})
    return {"productId": 1, "name": name, "extendedData": extended}


def test_single_cards_are_not_sealed():
    assert not classify.is_sealed(product("Charizard ex - 006/165", number="006/165", rarity="Double Rare"))


def test_products_without_number_and_rarity_are_sealed():
    assert classify.is_sealed(product("Delta Reign Booster Box"))


def test_sealed_wording_wins_even_when_a_rarity_is_present():
    assert classify.is_sealed(product("Delta Reign Elite Trainer Box", number="-", rarity="Promo"))


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Delta Reign Booster Box", "booster_box"),
        ("Delta Reign Booster Box Case", "case"),
        ("Delta Reign Elite Trainer Box Case", "case"),
        ("Delta Reign Half Booster Box", "half_booster_box"),
        ("Delta Reign Elite Trainer Box", "etb"),
        ("Delta Reign Pokemon Center Elite Trainer Box (Exclusive)", "etb"),
        ("Delta Reign Booster Bundle", "booster_bundle"),
        ("Delta Reign Build & Battle Box", "build_and_battle"),
        ("Delta Reign 3 Pack Blister [Seel]", "blister"),
        ("Delta Reign Sleeved Booster Pack", "sleeved_booster"),
        ("Delta Reign Booster Pack", "booster_pack"),
        ("Mega Charizard Tin", "tin"),
        ("30th Celebration Poster Collection", "poster_collection"),
        ("Prismatic Evolutions Super Premium Collection", "premium_collection"),
        ("First Partner Illustration Collection Series 1", "collection"),
        ("30th Celebration Sylveon ex Box", "box"),
        ("30th Celebration Battle Deck [Espeon ex]", "deck"),
        ("Pokemon Eevee 3 Ring Album", "other"),
    ],
)
def test_product_type(name: str, expected: str):
    assert classify.product_type(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Delta Reign Single Pack Blister (Target Exclusive) [Keldeo]", "Target"),
        ("Delta Reign Pokemon Center Elite Trainer Box (Exclusive)", "Pokemon Center"),
        ("Pokémon Center Elite Trainer Box", "Pokemon Center"),
        ("Charizard Collection (Walmart Exclusive)", "Walmart"),
        ("Blaziken ex Premium Collection (Sam's Club Exclusive)", "Sam's Club"),
        ("Delta Reign Booster Box", None),
    ],
)
def test_exclusive_retailer(name: str, expected: str | None):
    assert classify.exclusive_retailer(name) == expected


@pytest.mark.parametrize(
    ("group_name", "expected"),
    [
        ("SV: Prismatic Evolutions", "prismatic evolutions"),
        ("ME06: Delta Reign", "delta reign"),
        ("ME: 30th Celebration", "30th celebration"),
        ("Scarlet & Violet 151", "scarlet & violet 151"),
    ],
)
def test_set_key_strips_era_prefix(group_name: str, expected: str):
    assert classify.set_key(group_name) == expected


def test_digital_code_cards_are_not_sealed_inventory():
    assert not classify.is_sealed(product("Code Card - 30th Celebration Elite Trainer Box"))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-11-06T00:00:00", "2026-11-06"),
        ("2026-11-06", "2026-11-06"),
        # tcgcsv stamps undated legacy groups with its build time.
        ("2026-09-25T20:00:05.9994058Z", None),
        (None, None),
    ],
)
def test_known_date_rejects_build_time_placeholders(value, expected):
    assert classify.known_date(value) == expected
