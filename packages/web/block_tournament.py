"""Block tournament — judge-as-admission for the block library.

The library only grows with blocks that already clear the bar. This is the
mechanism: render each candidate block in isolation (a neutral harness page), score
it with the *same* independent judge the production loop uses, and admit only the
top survivors. The fitness function the fleet ships against IS the admission test —
so generic, AI-house-style output is filtered out by the very `ai_house_style`
penalty the rubric already encodes.

This module is the pure, testable orchestration: candidates in, ranked results +
admitted entries out, with ``render`` and ``judge`` injected (no npm, no Chromium,
no API key in a unit test). The live wrapper (`scripts/agency/design_loop.py
block-tournament`) supplies the real astro-harness render + Gemini judge.

Admission ≠ clearance. A passing generated block is *admitted* (recorded with its
judge score) but not *cleared* — it carries the same production-clearance waiver as
generated imagery and cannot enter a build until the founder clears it.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from packages.web.block_library import (
    TIER_FLEET,
    BlockEntry,
    BlockLibrary,
)
from packages.web.design_studio import VisualScore

# The homogenization gate is the whole point — a block that reads as generic AI work
# is rejected even if it scores well elsewhere. Callers may pass slot-appropriate
# extras (e.g. hero_impact for a hero block).
DEFAULT_CRITICAL = frozenset({"ai_house_style"})
DEFAULT_MIN_OVERALL = 75  # a single block on a neutral page; the full page bar is 80
DEFAULT_FLOOR = 4
GENERATED_BLOCKS_DIR = "../blocks/generated"  # relative to src/pages/index.astro


@dataclass(frozen=True)
class BlockCandidate:
    """One block proposed for the library — its source plus where it could live."""

    id: str
    slot: str
    component: str  # Astro component name (unique; e.g. "StitchHeroA1")
    source: str  # claude | stitch | figma
    astro: str  # the .astro component source code
    archetype_affinity: tuple[str, ...] = ()
    license: str = ""
    prompt: str = ""

    @property
    def component_path(self) -> str:
        return f"{GENERATED_BLOCKS_DIR}/{self.component}.astro"


@dataclass(frozen=True)
class CandidateResult:
    """A scored candidate."""

    candidate: BlockCandidate
    scores: list[VisualScore]
    overall: float  # mean(scores) * 20, 0-100
    passed: bool
    reasons: list[str] = field(default_factory=list)  # why it failed (empty if passed)


@dataclass(frozen=True)
class TournamentResult:
    ranked: list[CandidateResult]  # all candidates, best overall first
    admitted: list[CandidateResult]  # the kept passers (top-K)


# (candidate) -> {"desktop": path, "mobile": path, ...}
Render = Callable[[BlockCandidate], dict]
# (screenshots) -> per-category VisualScores
Judge = Callable[[dict], Sequence[VisualScore]]


def _overall(scores: Sequence[VisualScore]) -> float:
    return round(statistics.mean(s.score for s in scores) * 20, 1) if scores else 0.0


def evaluate(
    candidate: BlockCandidate,
    *,
    render: Render,
    judge: Judge,
    min_overall: int = DEFAULT_MIN_OVERALL,
    floor: int = DEFAULT_FLOOR,
    critical: frozenset[str] = DEFAULT_CRITICAL,
) -> CandidateResult:
    """Render + judge one candidate and decide pass/fail against the admission bar."""

    scores = list(judge(render(candidate)))
    overall = _overall(scores)
    by_cat = {s.category: s.score for s in scores}
    reasons: list[str] = []
    if overall < min_overall:
        reasons.append(f"overall {overall} < {min_overall}")
    for cat in sorted(critical):
        got = by_cat.get(cat)
        if got is None:
            reasons.append(f"missing critical category {cat}")
        elif got < floor:
            reasons.append(f"{cat} {got} < {floor}")
    return CandidateResult(
        candidate=candidate,
        scores=scores,
        overall=overall,
        passed=not reasons,
        reasons=reasons,
    )


def tournament(
    candidates: Sequence[BlockCandidate],
    *,
    render: Render,
    judge: Judge,
    keep: int = 6,
    min_overall: int = DEFAULT_MIN_OVERALL,
    floor: int = DEFAULT_FLOOR,
    critical: frozenset[str] = DEFAULT_CRITICAL,
) -> TournamentResult:
    """Score every candidate, rank by overall, admit the top ``keep`` passers."""

    results = [
        evaluate(
            c,
            render=render,
            judge=judge,
            min_overall=min_overall,
            floor=floor,
            critical=critical,
        )
        for c in candidates
    ]
    ranked = sorted(results, key=lambda r: r.overall, reverse=True)
    admitted = [r for r in ranked if r.passed][: max(0, keep)]
    return TournamentResult(ranked=ranked, admitted=admitted)


def admit(
    library: BlockLibrary,
    admitted: Sequence[CandidateResult],
    *,
    admitted_at: str,
    tier: str = TIER_FLEET,
    cleared: bool = False,
) -> BlockLibrary:
    """Record passing candidates in the library as un-cleared generated blocks.

    ``cleared`` defaults to False: a tournament win earns a block its judge score and
    a place in the registry, but not the right to ship — that's a separate founder
    waiver (mirrors generated imagery). ``admitted_at`` is passed in (the pure layer
    never reads the clock, so it stays deterministic and resumable).
    """

    for result in admitted:
        c = result.candidate
        library.add(
            BlockEntry(
                id=c.id,
                component=c.component,
                component_path=c.component_path,
                slot=c.slot,
                archetype_affinity=c.archetype_affinity,
                source=c.source,
                license=c.license,
                judge_score=round(result.overall / 20, 3),
                admitted_at=admitted_at,
                tier=tier,
                cleared=cleared,
            )
        )
    return library
