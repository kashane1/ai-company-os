"""Tests for the quality loop + calibration (design engine Phase 6).

Locks the control flow that guarantees quality without trusting a single
self-scoring model: builder≠judge (injected), gate-not-gradient (never auto-ship
on score), best-iteration on non-convergence, graceful degradation, and a
calibration harness that halts on judge drift.
"""

from __future__ import annotations

from packages.web.design_loop import (
    GoldSample,
    calibrate,
    revision_brief,
    run_design_loop,
)
from packages.web.design_studio import VisualScore, review_visual_quality

SHOTS = {"desktop": "/d.png", "mobile": "/m.png"}


def _scores(values: dict[str, int]) -> list[VisualScore]:
    return [VisualScore(cat, v, "note") for cat, v in values.items()]


STRONG = {
    "visual_thesis": 5, "hero_impact": 5, "imagery_art_direction": 4,
    "typography": 4, "layout_composition": 4, "copy_specificity": 5,
}
WEAK = {
    "visual_thesis": 2, "hero_impact": 3, "imagery_art_direction": 2,
    "typography": 3, "layout_composition": 3, "copy_specificity": 4,
}


def test_loop_converges_then_requires_signoff() -> None:
    # Judge improves on the 2nd iteration; the loop stops and never auto-ships.
    seq = [_scores(WEAK), _scores(STRONG)]
    counter = [0]
    builds = [0]

    def build(i, brief):
        builds[0] += 1

    def judge(_):
        s = seq[counter[0]]
        counter[0] += 1
        return s

    result = run_design_loop(build=build, capture=lambda: SHOTS, judge=judge, max_iters=4)
    assert result.passed is True
    assert result.needs_signoff is True  # founder disposes, no auto-ship
    assert len(result.iterations) == 2
    assert builds[0] == 2
    # The failing first iteration produced a revision brief that fed the rebuild.
    assert result.iterations[0].passed is False


def test_non_convergence_returns_best_iteration() -> None:
    # Three weak iterations with a clear best (highest overall) in the middle.
    seqs = [_scores({**WEAK, "hero_impact": 1}), _scores(WEAK), _scores({**WEAK, "typography": 1})]
    counter = [0]

    def judge(_):
        s = seqs[counter[0]]
        counter[0] += 1
        return s

    result = run_design_loop(
        build=lambda i, b: None, capture=lambda: SHOTS, judge=judge, max_iters=3
    )
    assert result.passed is False
    assert result.needs_signoff is False
    assert result.halted_reason == "max_iters"
    # Best = iteration 1 (plain WEAK scores the highest overall of the three).
    assert result.best_index == 1


def test_judge_error_degrades_gracefully() -> None:
    def boom(_):
        raise RuntimeError("gemini down")

    result = run_design_loop(
        build=lambda i, b: None, capture=lambda: SHOTS, judge=boom, max_iters=3
    )
    assert result.passed is False
    assert "error" in result.halted_reason
    assert "gemini down" in result.halted_reason


def test_revision_brief_lists_failing_categories() -> None:
    report = review_visual_quality(scores=_scores(WEAK), screenshots=SHOTS)
    brief = revision_brief(report)
    assert "visual_thesis" in brief.failing_categories
    assert "imagery_art_direction" in brief.failing_categories
    assert "copy_specificity" not in brief.failing_categories  # scored 4, at floor
    assert brief.notes["visual_thesis"] == "note"


def test_calibration_detects_judge_drift() -> None:
    gold = [
        GoldSample(id="known-good", screenshots=SHOTS, expected="good"),
        GoldSample(id="known-bad", screenshots=SHOTS, expected="bad"),
    ]
    # A well-calibrated judge: scores good samples strong, bad samples weak.
    honest = calibrate(
        lambda s: _scores(STRONG) if s is SHOTS else _scores(WEAK), gold[:1]
    )
    assert honest.drifted is False

    # A drifted judge that rates everything strong → misclassifies known-bad.
    drifted = calibrate(lambda s: _scores(STRONG), gold)
    assert drifted.drifted is True
    assert any("known-bad" in m for m in drifted.mismatches)


def test_loop_requires_at_least_one_iteration_scored() -> None:
    # An immediate pass on iteration 0.
    result = run_design_loop(
        build=lambda i, b: None, capture=lambda: SHOTS, judge=lambda s: _scores(STRONG), max_iters=2
    )
    assert result.passed is True
    assert len(result.iterations) == 1
    assert result.best is not None and result.best.overall >= 80
