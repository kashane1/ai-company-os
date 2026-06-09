"""Library metrics — is the design space actually wider, and is it diverse?

Widening the block library only matters if it shows up in the output: more eligible
blocks per slot (a wider search space) and a spread of blocks actually used across
builds (not one block dominating). These are the compounding signals the plan's
Phase 6 asks for — kept as pure functions so the CLI can assemble a report from real
artifacts (the library manifest + the compositions a run produced).
"""

from __future__ import annotations

import statistics
from collections import Counter

from packages.web.block_library import SLOTS, TIER_FLEET, BlockLibrary

_TIER_VISIBILITY = {TIER_FLEET: {TIER_FLEET}, "premium": {TIER_FLEET, "premium"}}


def slot_coverage(library: BlockLibrary, *, tier: str = TIER_FLEET) -> dict[str, int]:
    """Cleared, eligible blocks per slot — how many options the loop can search."""

    visible = _TIER_VISIBILITY[tier]
    counts: Counter[str] = Counter()
    for entry in library.entries:
        if entry.cleared and entry.tier in visible:
            counts[entry.slot] += 1
    return {slot: counts.get(slot, 0) for slot in SLOTS}


def search_space_width(library: BlockLibrary, *, tier: str = TIER_FLEET) -> int:
    """A coarse 'how wide is the space' signal — total eligible blocks across slots.

    Grows as admitted blocks are cleared, so a before/after delta quantifies the lift.
    """

    return sum(slot_coverage(library, tier=tier).values())


def block_usage(compositions: list) -> dict[str, int]:
    """Count component usage across builds.

    ``compositions`` is a list of either component-name lists or objects with a
    ``blocks`` attribute of items carrying ``.component``.
    """

    counts: Counter[str] = Counter()
    for comp in compositions:
        if isinstance(comp, list):
            names = comp
        else:
            names = [b.component for b in comp.blocks]
        counts.update(names)
    return dict(counts)


def usage_distribution(usage: dict[str, int]) -> dict[str, float]:
    total = sum(usage.values()) or 1
    return {name: round(count / total, 3) for name, count in usage.items()}


def dominance_flags(usage: dict[str, int], *, threshold: float = 0.6) -> list[str]:
    """Components used in more than ``threshold`` of all placements — diversity risk.

    If one block dominates, the library isn't really wider in practice; this is the
    guard the plan asks for against silent homogenization.
    """

    dist = usage_distribution(usage)
    return sorted(name for name, frac in dist.items() if frac > threshold)


def pass_rate(passed_flags: list[bool]) -> float:
    """Fraction of builds that passed (e.g. first-iteration pass over a prospect set)."""

    return round(sum(1 for p in passed_flags if p) / len(passed_flags), 3) if passed_flags else 0.0


def score_spread(overalls: list[float]) -> dict[str, float]:
    """min/max/mean/stdev of overall scores — variance signal across a run set."""

    if not overalls:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "stdev": 0.0}
    return {
        "min": round(min(overalls), 1),
        "max": round(max(overalls), 1),
        "mean": round(statistics.mean(overalls), 1),
        "stdev": round(statistics.pstdev(overalls), 1),
    }


def library_report(
    library: BlockLibrary,
    *,
    compositions: list | None = None,
    tier: str = TIER_FLEET,
    dominance_threshold: float = 0.6,
) -> dict:
    """Bundle the metrics into one report dict (what the CLI prints/persists)."""

    report: dict = {
        "tier": tier,
        "search_space_width": search_space_width(library, tier=tier),
        "slot_coverage": slot_coverage(library, tier=tier),
        "blocks_total": len(library.entries),
        "blocks_cleared": sum(1 for e in library.entries if e.cleared),
    }
    if compositions:
        usage = block_usage(compositions)
        report["block_usage"] = usage
        report["usage_distribution"] = usage_distribution(usage)
        report["dominance_flags"] = dominance_flags(usage, threshold=dominance_threshold)
    return report
