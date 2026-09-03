"""Tests for card-class derivation.

Every case here is a real product observed in the tcgcsv feed, because the
whole point of this module is coping with what the feed actually sends rather
than what it ought to.
"""

from __future__ import annotations

import pytest

from ingest.classify import ENERGY, POKEMON, TRAINER, classify, coerce_hp


@pytest.mark.parametrize(
    "card_type, stage, hp, expected",
    [
        # Modern Pokemon: Card Type holds the energy type.
        ("Fire", "Basic", "70", POKEMON),
        ("Water", "Stage 2", "170", POKEMON),
        # Dual types and feed typos still read as Pokemon.
        ("Darkness Metal", "Basic", "110", POKEMON),
        ("Lighnting", "Basic", "60", POKEMON),
        ("Fighting/Darkness", "Basic", "90", POKEMON),
        # The finish leaked into Card Type on a handful of cards (Cyclizar ex,
        # Ditto). Not a trainer or energy label, so Pokemon is still right.
        ("Normal", "Basic", "120", POKEMON),
        # Plasma-era cards: Card Type is blank and Stage carries the signal.
        # These are the 295 cards that were previously unclassifiable.
        (None, "Stage 1", "90", POKEMON),
        ("", "Basic", "170", POKEMON),
        # Trainers. Note HP is present but "0" — it must not vote Pokemon.
        ("Item", "Item", "0", TRAINER),
        ("Supporter", "Supporter", "0", TRAINER),
        ("Stadium", "Stadium", "0", TRAINER),
        ("Trainer", None, None, TRAINER),
        ("Trainer - Item", None, None, TRAINER),
        ("Trainer — Item", None, None, TRAINER),  # em dash variant in the feed
        ("Pokémon Tool", None, None, TRAINER),
        ("Trainer - Pokemon Tool", None, None, TRAINER),
        ("Technical Machine", None, None, TRAINER),
        ("TM", None, None, TRAINER),
        ("Rocket's Secret Machine", None, None, TRAINER),
        ("Support", None, None, TRAINER),
        # Energy.
        ("Basic Energy", "Energy", "0", ENERGY),
        ("Special Energy", "Energy", "0", ENERGY),
        ("Basic Lightning Energy", None, None, ENERGY),
        ("Special Rainbow Energy", None, None, ENERGY),
        ("Energy", "Energy", "0", ENERGY),
        (None, "Basic Energy", "0", ENERGY),
    ],
)
def test_classify_real_feed_values(card_type, stage, hp, expected):
    assert classify(card_type, stage, hp)[0] == expected


def test_card_type_beats_stage_and_hp():
    """Base Set's Clefairy Doll is a Trainer that reports HP 10 and no Stage.

    Only Card Type gets it right, which is why it takes precedence.
    """
    assert classify("Trainer", None, "10") == (TRAINER, None)


def test_hp_is_the_last_resort_not_the_first():
    """A Trainer with HP "0" and no other signal is not a Pokemon."""
    assert classify(None, None, "0") == (None, None)
    # ...but a positive HP with nothing else is the best guess available.
    assert classify(None, None, "60") == (POKEMON, None)


def test_unclassifiable_returns_none_rather_than_guessing():
    assert classify(None, None, None) == (None, None)
    assert classify("", "", "") == (None, None)


@pytest.mark.parametrize(
    "card_type, expected_kind",
    [
        ("Item", "Item"),
        ("Trainer - Item", "Item"),
        ("Supporter", "Supporter"),
        ("Trainer - Supporter", "Supporter"),
        ("Support", "Supporter"),
        ("Stadium", "Stadium"),
        ("Tool", "Tool"),
        ("Pokemon Tool", "Tool"),
        ("Trainer - Pokemon Tool", "Tool"),
        ("Technical Machine", "Technical Machine"),
        ("TM", "Technical Machine"),
        # A bare "Trainer" states no kind, and inventing one would be a lie.
        ("Trainer", None),
    ],
)
def test_trainer_kind(card_type, expected_kind):
    card_class, kind = classify(card_type, None, None)
    assert card_class == TRAINER
    assert kind == expected_kind


def test_non_trainers_have_no_trainer_kind():
    assert classify("Fire", "Basic", "70")[1] is None
    assert classify("Basic Energy", "Energy", "0")[1] is None


@pytest.mark.parametrize(
    "value, expected",
    [("70", 70), ("0", 0), (0, 0), (110, 110), (None, 0), ("", 0), ("n/a", 0), (" 90 ", 90)],
)
def test_coerce_hp(value, expected):
    assert coerce_hp(value) == expected


# ---------------------------------------------------------------------------
# Name fallback for energy cards the type fields do not identify
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name, card_type",
    [
        # The type fields say "Metal", which is indistinguishable from a Metal
        # Pokemon without the name.
        ("Metal Energy - 94/109 (EX Ruby & Sapphire)", "Metal"),
        # No type fields at all — these were unclassifiable before.
        ("Basic Grass Energy - MEE 001", None),
        ("Basic Fire Energy - MEE 002 (Cosmos Holo)", None),
        ("Team Rocket's Energy - 182/182", None),
        ("Team Rocket's Energy", None),
    ],
)
def test_energy_cards_are_recovered_from_their_name(name, card_type):
    assert classify(card_type, None, None, name)[0] == ENERGY


@pytest.mark.parametrize(
    "name, card_type, hp",
    [
        # "Energy Holo" and "Energy Symbol Pattern" are print variants. These
        # are Pokemon and must stay Pokemon.
        ("Pansear - 21/114 (Energy Holo)", "Fire", "60"),
        ("Erika's Oddish (Energy Symbol Pattern)", "Grass", "60"),
        ("Beautifly - 013/217 (Energy Symbol Pattern)", "Grass", "130"),
        ("Chikorita (Energy Symbol Pattern)", "Grass", "70"),
    ],
)
def test_print_variants_mentioning_energy_stay_pokemon(name, card_type, hp):
    assert classify(card_type, "Basic", hp, name)[0] == POKEMON


def test_name_fallback_never_overrides_a_real_pokemon_signal():
    """A Stage or a positive HP outranks the name, whatever the name says."""
    assert classify(None, "Basic", "60", "Basic Fire Energy")[0] == POKEMON
    assert classify(None, None, "60", "Basic Fire Energy")[0] == POKEMON


def test_trainers_referencing_energy_are_not_energy_cards():
    """"Energy Retrieval" is an Item. Its type fields say so, and the name rule
    must not fire because the name does not end in "Energy"."""
    assert classify("Item", "Item", "0", "Energy Retrieval")[0] == TRAINER
    assert classify("Trainer", None, None, "Super Energy Removal")[0] == TRAINER
    assert classify("Trainer", None, None, "Energy Search")[0] == TRAINER
