"""Tests for eBay title and item-specific generation."""

from __future__ import annotations

import pytest
from inventory import ebay_listing as el


def card(**overrides):
    base = {
        "card_name": "Charizard ex - 199/165",
        "card_number": "199/165",
        "set_name": "SV: Scarlet & Violet 151",
        "set_abbreviation": "MEW",
        "rarity": "Special Illustration Rare",
        "sub_type": "Holofoil",
        "released_on": "2023-09-22",
        "hp": 330,
        "stage": "Stage 2",
        "card_type": "Fire",
    }
    base.update(overrides)
    return base


# ─── Name and set cleaning ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "name, number, expected",
    [
        ("Iono - 269/193", "269/193", "Iono"),
        ("Charizard ex - 199/165", "199/165", "Charizard ex"),
        ("Tepig - 050", "050", "Tepig"),
        ("Umbreon VMAX (Alternate Art Secret)", "215/203", "Umbreon VMAX (Alternate Art Secret)"),
        ("AZ (117 Full Art)", "117/119", "AZ (117 Full Art)"),
        # The year is part of this card's identity and must survive.
        ("AZ - 2015 (Patrick Martinez)", "91/119", "AZ - 2015"),
    ],
)
def test_card_name_cleaning(name, number, expected):
    assert el.clean_card_name(name, number) == expected


def test_a_year_is_not_mistaken_for_a_collector_number():
    """Without the real number, "- 2015" and "- 050" are the same shape."""
    assert el.clean_card_name("AZ - 2015 (Patrick Martinez)", "91/119") == "AZ - 2015"
    assert el.character_from("AZ - 2015 (Patrick Martinez)", "91/119") == "AZ"


@pytest.mark.parametrize(
    "set_name, expected",
    [
        ("SWSH07: Evolving Skies", "Evolving Skies"),
        ("SV02: Paldea Evolved", "Paldea Evolved"),
        ("SV: Scarlet & Violet 151", "Scarlet & Violet 151"),
        ("XY - Phantom Forces", "Phantom Forces"),
        # "EX" here is the era name, not a code prefix — it must stay.
        ("EX FireRed & LeafGreen", "EX FireRed & LeafGreen"),
    ],
)
def test_set_name_cleaning(set_name, expected):
    assert el.clean_set_name(set_name) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Charizard ex", "Charizard"),
        ("Umbreon VMAX", "Umbreon"),
        ("Umbreon V (Alternate Full Art)", "Umbreon"),
        ("Iono", "Iono"),
    ],
)
def test_character_extraction(name, expected):
    assert el.character_from(name) == expected


# ─── Titles ──────────────────────────────────────────────────────────────────

def test_title_never_exceeds_the_limit():
    result = el.build_title(card(), "NM")
    assert result.length <= el.MAX_TITLE_LENGTH


def test_title_leads_with_name_number_and_set():
    result = el.build_title(card(), "NM")
    assert result.title.startswith("Charizard ex 199/165 Scarlet & Violet 151")


def test_long_titles_degrade_rather_than_truncate():
    """A truncated word matches nothing; an abbreviation still matches."""
    result = el.build_title(
        card(card_name="Umbreon VMAX (Alternate Art Secret)", card_number="215/203",
             set_name="SWSH07: Evolving Skies", rarity="Secret Rare"),
        "NM",
    )
    assert result.length <= el.MAX_TITLE_LENGTH
    assert not result.title.endswith("-")
    # Whatever survived must be whole words from the source.
    assert "Umbreon VMAX (Alternate Art Secret)" in result.title


def test_condition_is_the_first_thing_dropped():
    """It is already an item specific, so it is the cheapest token to lose."""
    long_card = card(
        card_name="Umbreon VMAX (Alternate Art Secret)",
        card_number="215/203",
        set_name="SWSH07: Evolving Skies",
        rarity="Secret Rare",
    )
    result = el.build_title(long_card, "NM")
    assert "NM" in result.dropped


def test_rarity_abbreviates_before_being_dropped():
    result = el.build_title(
        card(card_name="Iono", card_number="269/193", set_name="SV02: Paldea Evolved"), "NM"
    )
    assert "Special Illustration Rare" in result.title or "SIR" in result.title


def test_repeated_words_are_not_duplicated():
    """A promo set whose rarity is also "Promo" must not read "Promo Promo"."""
    result = el.build_title(
        card(card_name="Tepig", card_number="050", set_name="Mega Evolution Promo",
             rarity="Promo", set_abbreviation=""),
        "NM",
    )
    assert "Promo Promo" not in result.title


def test_normal_finish_contributes_no_token():
    result = el.build_title(card(sub_type="Normal", rarity="Common"), "NM")
    assert "Normal" not in result.title


def test_first_edition_survives_in_the_title():
    """High-value search term on vintage; it must not be dropped silently."""
    result = el.build_title(
        card(card_name="Charizard", card_number="4/102", set_name="Base Set",
             rarity="Holo Rare", sub_type="1st Edition Holofoil", set_abbreviation=""),
        "NM",
    )
    assert "1st Ed" in result.title


# ─── Aspects ─────────────────────────────────────────────────────────────────

def test_aspects_cover_the_filterable_fields():
    aspects = el.build_aspects(card(), "NM")
    for required in ("Game", "Set", "Card Number", "Character", "Rarity",
                     "Card Condition", "Finish", "Language", "Graded"):
        assert required in aspects, f"missing {required}"


def test_condition_maps_to_ebays_vocabulary():
    assert el.build_aspects(card(), "NM")["Card Condition"] == "Near Mint or Better"
    assert el.build_aspects(card(), "LP")["Card Condition"] == "Lightly Played (Excellent)"
    assert el.build_aspects(card(), "DMG")["Card Condition"] == "Damaged"


def test_reverse_holo_is_its_own_finish():
    aspects = el.build_aspects(card(sub_type="Reverse Holofoil"), "NM")
    assert aspects["Finish"] == "Reverse Holo"


def test_first_edition_is_recorded_as_a_feature():
    aspects = el.build_aspects(card(sub_type="1st Edition Holofoil"), "NM")
    assert "1st Edition" in aspects["Features"]


def test_catalog_extras_become_aspects():
    aspects = el.build_aspects(card(), "NM")
    assert aspects["HP"] == "330"
    assert aspects["Stage"] == "Stage 2"
    assert aspects["Energy Type"] == "Fire"


def test_empty_values_are_omitted_rather_than_sent_blank():
    aspects = el.build_aspects(card(rarity=None, hp=None, stage=None, card_type=None), "NM")
    assert "Rarity" not in aspects
    assert "HP" not in aspects
    assert all(value for value in aspects.values())


def test_description_states_condition_without_overselling():
    text = el.build_description(card(), "MP")
    assert "Moderately Played" in text
    assert "Scarlet & Violet 151" in text
