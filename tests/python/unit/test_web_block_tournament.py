"""Tests for the block tournament (judge-as-admission).

Locks the contract that the library only grows with blocks that clear the bar, that
the ai_house_style gate can sink a candidate that otherwise scores well, and that a
tournament win admits an *un-cleared* generated block (judge ≠ founder clearance).
Render + judge are injected, so this runs with no npm / Chromium / API key.
"""

from __future__ import annotations

from packages.web.block_library import BlockLibrary, TIER_FLEET
from packages.web.block_tournament import (
    BlockCandidate,
    admit,
    evaluate,
    tournament,
)
from packages.web.design_studio import RUBRIC_CATEGORIES, VisualScore


def _scores(value: int, **overrides: int) -> list[VisualScore]:
    return [
        VisualScore(category=c, score=overrides.get(c, value), note="t")
        for c in RUBRIC_CATEGORIES
    ]


def _candidate(cid: str, component: str = "GenHero") -> BlockCandidate:
    return BlockCandidate(
        id=cid,
        slot="hero",
        component=component,
        source="stitch",
        astro="<section>...</section>",
        archetype_affinity=("service-area-cinematic",),
        license="generated",
    )


def _render(_c: BlockCandidate) -> dict:
    return {"desktop": "/tmp/desktop.png"}


# --------------------------------------------------------------------------- #
# evaluate
# --------------------------------------------------------------------------- #
def test_strong_candidate_passes() -> None:
    res = evaluate(_candidate("c1"), render=_render, judge=lambda s: _scores(5))
    assert res.passed
    assert res.overall == 100.0
    assert res.reasons == []


def test_low_overall_fails() -> None:
    res = evaluate(_candidate("c2"), render=_render, judge=lambda s: _scores(3))
    assert not res.passed
    assert any("overall" in r for r in res.reasons)


def test_ai_house_style_gate_sinks_an_otherwise_strong_block() -> None:
    # everything 5 except the homogenization gate -> must fail despite a high mean
    res = evaluate(
        _candidate("c3"),
        render=_render,
        judge=lambda s: _scores(5, ai_house_style=2),
    )
    assert not res.passed
    assert any("ai_house_style" in r for r in res.reasons)


# --------------------------------------------------------------------------- #
# tournament
# --------------------------------------------------------------------------- #
def test_tournament_ranks_and_keeps_top_passers() -> None:
    cands = [_candidate("a", "A"), _candidate("b", "B"), _candidate("c", "C")]
    by_id = {
        "A": _scores(5),  # 100, pass
        "B": _scores(4),  # 80, pass
        "C": _scores(3),  # 60, fail
    }

    # render returns the component so the judge can branch on it
    def render(c: BlockCandidate) -> dict:
        return {"desktop": c.component}

    def judge(shots: dict) -> list[VisualScore]:
        return by_id[shots["desktop"]]

    result = tournament(cands, render=render, judge=judge, keep=2)
    assert [r.candidate.component for r in result.ranked] == ["A", "B", "C"]
    assert [r.candidate.component for r in result.admitted] == ["A", "B"]  # C failed


def test_keep_limits_admissions() -> None:
    cands = [_candidate(str(i), f"C{i}") for i in range(4)]
    result = tournament(
        cands, render=_render, judge=lambda s: _scores(5), keep=2
    )
    assert len(result.admitted) == 2
    assert len(result.ranked) == 4


# --------------------------------------------------------------------------- #
# admit — judge win is not a clearance to ship
# --------------------------------------------------------------------------- #
def test_admit_records_uncleared_generated_entry() -> None:
    lib = BlockLibrary()
    result = tournament([_candidate("h1", "GenHero")], render=_render, judge=lambda s: _scores(5))
    admit(lib, result.admitted, admitted_at="2026-06-09T00:00:00Z")

    assert len(lib.entries) == 1
    entry = lib.entries[0]
    assert entry.id == "h1"
    assert entry.component_path == "../blocks/generated/GenHero.astro"
    assert entry.source == "stitch"
    assert entry.judge_score == 5.0
    assert entry.tier == TIER_FLEET
    assert entry.cleared is False  # admitted, but not cleared to ship
    # because it's un-cleared, it is not yet a build candidate
    assert lib.candidates("hero", "service-area-cinematic") == []
