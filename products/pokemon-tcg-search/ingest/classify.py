"""Classify a card as Pokemon, Trainer or Energy.

TCGplayer has no single "what kind of card is this" field, so this derives one
from the three extendedData fields that carry the signal. Kept separate from
catalog.py so the precedence rules can be unit tested without the network.

What the feed actually gives us, measured across sets from Base Set to SV09:

  * `Card Type` is the curated field but it is SPARSE — only 13 of 146 products
    in Plasma Storm carry it, and 295 cards in the full catalog have none. It
    holds an energy type ("Fire") for Pokemon and a trainer label ("Item") for
    the rest.
  * `Stage` is far better populated and doubles as a type field: Pokemon get
    "Basic"/"Stage 1"/"VMAX", while non-Pokemon repeat their own class there
    ("Item", "Supporter", "Stadium", "Energy").
  * `HP` is present on non-Pokemon too, but always as the string "0". Only a
    value above zero means Pokemon.

`Card Type` wins over `Stage` because it is hand-maintained where it exists:
Base Set's Clefairy Doll is a Trainer that carries HP 10 and no Stage, and only
`Card Type` gets it right. HP is the last resort, used when the other two are
blank.
"""

from __future__ import annotations

import re

POKEMON = "Pokemon"
TRAINER = "Trainer"
ENERGY = "Energy"

# Trainer labels as they appear in `Card Type` / `Stage`, matched as substrings
# so the feed's many spellings all land ("Trainer - Item", "Trainer — Item",
# "Pokemon Tool", "Pokémon Tool", "Trainer - Pokemon Tool"). Verified against
# every distinct value in the catalog: no energy type contains any of these.
_TRAINER_MARKERS = (
    "trainer",
    "item",
    "supporter",
    "support",
    "stadium",
    "tool",
    "machine",  # "Technical Machine", "Rocket's Secret Machine"
)

# "TM" is the only trainer label short enough to collide as a substring, so it
# is matched whole rather than with _TRAINER_MARKERS.
_TRAINER_EXACT = ("tm",)

# Which kind of Trainer, for the finer-grained filter. Ordered because
# "Trainer - Pokemon Tool" matches both "tool" and the generic "trainer", and
# the specific answer is the useful one. Generic "Trainer" deliberately maps to
# None: the feed simply did not say which kind it is.
_TRAINER_KINDS = (
    ("machine", "Technical Machine"),
    ("tm", "Technical Machine"),
    ("tool", "Tool"),
    ("stadium", "Stadium"),
    ("supporter", "Supporter"),
    ("support", "Supporter"),
    ("item", "Item"),
)


def coerce_hp(value: object) -> int:
    """The feed sends HP as a string, and as "0" for every non-Pokemon."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


# Trailing print-variant parentheticals and collector-number suffixes, stripped
# before reading a name. "Basic Fire Energy - MEE 002 (Cosmos Holo)" has both.
_NAME_SUFFIXES = re.compile(r"\s*\([^()]*\)\s*$|\s+-\s+[^-]*$")


def _looks_like_energy_card(name: str) -> bool:
    """True when the card's own name, stripped of print noise, ends in "Energy".

    Needed because a handful of energy cards carry a bare energy type in
    `Card Type` ("Metal Energy" typed as "Metal") with no Stage or HP, which is
    indistinguishable from a Pokemon on the type fields alone.

    Matching on the *end* of the stripped name is what keeps the 143 Pokemon
    whose names merely mention energy out of it: "Pansear - 21/114 (Energy
    Holo)" and "Erika's Oddish (Energy Symbol Pattern)" reduce to "Pansear" and
    "Erika's Oddish", while "Basic Fire Energy - MEE 002 (Cosmos Holo)" reduces
    to "Basic Fire Energy".
    """
    stripped = (name or "").strip()
    previous = None
    while stripped != previous:
        previous = stripped
        stripped = _NAME_SUFFIXES.sub("", stripped).strip()
    return stripped.lower().endswith("energy")


def _classify_label(label: str) -> str | None:
    """Read one `Card Type` or `Stage` value. None when it says nothing."""
    label = label.strip().lower()
    if not label:
        return None
    if "energy" in label:
        return ENERGY
    if label in _TRAINER_EXACT or any(m in label for m in _TRAINER_MARKERS):
        return TRAINER
    # Anything else is an energy type ("Fire", "Darkness Metal", the misspelled
    # "Lighnting") or a Pokemon stage ("Basic", "Stage 2", "VMAX"). Both mean
    # Pokemon, and defaulting here keeps new stage names working without a
    # code change.
    return POKEMON


def classify(
    card_type: str | None,
    stage: str | None,
    hp: object = None,
    name: str | None = None,
) -> tuple[str | None, str | None]:
    """Return (card_class, trainer_kind).

    `card_class` is None only when the feed gave us no usable signal at all.
    `trainer_kind` is set only for Trainers whose specific kind is stated.
    """
    # Neither Stage nor a real HP means nothing here confirms a Pokemon, so the
    # card's name is allowed to settle it. Gated this tightly on purpose: with
    # HP present the type fields are already trustworthy, and the name is not.
    has_pokemon_evidence = bool((stage or "").strip()) or coerce_hp(hp) > 0
    if not has_pokemon_evidence and _looks_like_energy_card(name or ""):
        return ENERGY, None

    card_class = None
    for value in (card_type, stage):
        card_class = _classify_label(value or "")
        if card_class is not None:
            break

    if card_class is None:
        card_class = POKEMON if coerce_hp(hp) > 0 else None

    if card_class != TRAINER:
        return card_class, None

    # Prefer whichever field names the kind; Card Type first, same as above.
    for value in (card_type, stage):
        label = (value or "").strip().lower()
        for marker, kind in _TRAINER_KINDS:
            if marker == "tm":
                if label == "tm":
                    return TRAINER, kind
            elif marker in label:
                return TRAINER, kind
    return TRAINER, None


CARD_CLASSES = (POKEMON, TRAINER, ENERGY)
TRAINER_KINDS = ("Item", "Supporter", "Stadium", "Tool", "Technical Machine")

__all__ = [
    "CARD_CLASSES",
    "coerce_hp",
    "ENERGY",
    "POKEMON",
    "TRAINER",
    "TRAINER_KINDS",
    "classify",
]
