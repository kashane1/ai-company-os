"""Block library — the growable search space for the design engine.

The v3 loop searches a *bounded* design space: a fixed set of art-directed blocks
(`scaffold/astro-premium/src/blocks/*.astro`) wired into `blocks_composer._VARIANTS`.
No matter how good the judge is, the loop can only converge to the best point inside
that fixed set. This module is the registry that lets the set **grow** — new blocks
authored by external tools (Stitch) or Claude, each admitted only after the judge
clears it, each carrying provenance + a clearance waiver like generated imagery.

It is the pure, testable core: a manifest of `BlockEntry` records + slot resolution +
a clearance gate. It deliberately mirrors `packages/web/imagery.py` (provenance +
`production_clearance`) so the legal/operational discipline carries over unchanged.

Knowledge of the *builtin* blocks (their components, import paths, archetype affinity)
lives in `blocks_composer.builtin_library()` — this module stays free of any
composer import so the dependency runs one way (composer → library).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# The canonical content slots a block can fill — the inverse of
# `blocks_composer._slot()`. A block declares the slot it serves, and the composer
# resolves each slot in a variant to a concrete block. The slot IS the interface:
# any block admitted for a slot must accept that slot's `data` shape.
SLOTS = ("hero", "split", "bento", "process", "fullbleed", "cta")

SOURCE_HAND = "hand"
SOURCE_CLAUDE = "claude"
SOURCE_STITCH = "stitch"
SOURCE_FIGMA = "figma"
_VALID_SOURCE = {SOURCE_HAND, SOURCE_CLAUDE, SOURCE_STITCH, SOURCE_FIGMA}
# A "generated" source produces output that needs a clearance waiver before it ships
# (same posture as generated imagery). Hand-authored blocks never block.
_GENERATED_SOURCES = {SOURCE_CLAUDE, SOURCE_STITCH, SOURCE_FIGMA}

TIER_FLEET = "fleet"
TIER_PREMIUM = "premium"
_VALID_TIER = {TIER_FLEET, TIER_PREMIUM}
# A fleet build may use only fleet blocks; a premium build may use both.
_TIER_VISIBILITY = {TIER_FLEET: {TIER_FLEET}, TIER_PREMIUM: {TIER_FLEET, TIER_PREMIUM}}


@dataclass(frozen=True)
class BlockEntry:
    """One block component in the library + its provenance and clearance state."""

    id: str
    component: str  # Astro component name, e.g. "CinematicHero"
    component_path: str  # import path relative to src/pages/index.astro
    slot: str  # one of SLOTS — the content contract the block fulfils
    archetype_affinity: tuple[str, ...] = ()  # empty = serves any archetype
    source: str = SOURCE_HAND
    license: str = ""
    judge_score: float = 0.0
    admitted_at: str = ""
    tier: str = TIER_FLEET
    cleared: bool = False

    def __post_init__(self) -> None:
        if self.slot not in SLOTS:
            raise ValueError(f"invalid slot: {self.slot}")
        if self.source not in _VALID_SOURCE:
            raise ValueError(f"invalid source: {self.source}")
        if self.tier not in _VALID_TIER:
            raise ValueError(f"invalid tier: {self.tier}")
        # JSON round-trips affinity as a list; normalise to a tuple so entries hash.
        object.__setattr__(self, "archetype_affinity", tuple(self.archetype_affinity))

    @property
    def generated(self) -> bool:
        return self.source in _GENERATED_SOURCES

    def serves(self, archetype: str) -> bool:
        return not self.archetype_affinity or archetype in self.archetype_affinity

    def to_dict(self) -> dict:
        data = asdict(self)
        data["archetype_affinity"] = list(self.archetype_affinity)
        return data


@dataclass
class BlockLibrary:
    """The registry of admitted blocks the composer searches."""

    entries: list[BlockEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"entries": [e.to_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, payload: dict) -> BlockLibrary:
        return cls(entries=[BlockEntry(**e) for e in payload.get("entries", [])])

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return path

    @classmethod
    def load(cls, path: Path) -> BlockLibrary:
        return cls.from_dict(json.loads(Path(path).read_text()))

    def add(self, entry: BlockEntry) -> None:
        """Add or replace an entry by id (admission is idempotent)."""

        self.entries = [e for e in self.entries if e.id != entry.id] + [entry]

    def candidates(
        self, slot: str, archetype: str, *, tier: str = TIER_FLEET
    ) -> list[BlockEntry]:
        """Cleared blocks eligible for this slot/archetype at this build tier.

        Un-cleared blocks are never eligible, so an admitted-but-uncleared generated
        block can sit in the library without ever silently entering a build.
        """

        visible = _TIER_VISIBILITY[tier]
        return [
            e
            for e in self.entries
            if e.slot == slot
            and e.cleared
            and e.tier in visible
            and e.serves(archetype)
        ]

    def resolve(
        self, slot: str, archetype: str, *, concept: str = "", tier: str = TIER_FLEET
    ) -> BlockEntry | None:
        """Deterministically pick one block for a slot (None → use the builtin).

        The choice is a stable hash of (concept, slot, archetype) so a given build is
        reproducible and two builds with different concepts can diverge — the same
        determinism principle as `blocks_composer._variant_index`. With a library that
        has exactly one candidate per slot (the builtin seed), this always returns that
        one block, so composition output is unchanged.
        """

        cands = sorted(self.candidates(slot, archetype, tier=tier), key=lambda e: e.id)
        if not cands:
            return None
        digest = hashlib.md5(f"{concept}|{slot}|{archetype}".encode()).hexdigest()
        return cands[int(digest, 16) % len(cands)]


def clearance_blockers(library: BlockLibrary) -> list[str]:
    """Generated blocks that are admitted but not yet founder-cleared for production.

    Mirrors `imagery.clearance_blockers`: hand-authored blocks never block; a generated
    block must carry an explicit clearance waiver before it can ship.
    """

    return [e.id for e in library.entries if e.generated and not e.cleared]


def library_cleared(path: Path) -> bool:
    """True if there's no library, or every generated block in it is cleared."""

    path = Path(path)
    if not path.exists():
        return True
    return not clearance_blockers(BlockLibrary.load(path))
