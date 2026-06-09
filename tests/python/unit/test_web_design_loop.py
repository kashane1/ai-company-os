"""Tests for the quality loop + calibration (design engine Phase 6 / v3).

Locks the control flow that guarantees quality without trusting a single
self-scoring model: builder≠judge (injected), gate-not-gradient (never auto-ship
on score), best-iteration on non-convergence, graceful degradation, plateau +
budget halts, and a calibration harness that halts on judge drift.

v3 note: the convergence test below proves the revision **brief is actually
consumed** by the build (the v2 test faked convergence with a hard-coded score
sequence and a build stub that ignored the brief — that is the anti-pattern this
file now guards against).
"""

from __future__ import annotations

from packages.web.design_loop import (
    BudgetGuard,
    GoldSample,
    calibrate,
    revision_brief,
    run_design_loop,
)
from packages.web.design_studio import VisualScore, review_visual_quality

SHOTS = {"desktop": "/d.png", "mobile": "/m.png"}


def _scores(values: dict[str, int]) -> list[VisualScore]:
    return [VisualScore(cat, v, "note") for cat, v in values.items()]


# v3 rubric: 12 dimensions (criticals: visual_thesis, hero_impact,
# imagery_art_direction, ai_house_style).
STRONG = {
    "visual_thesis": 5, "hero_impact": 5, "imagery_art_direction": 4,
    "typography": 4, "color_system": 4, "layout_composition": 4,
    "whitespace_depth": 4, "motion_quality": 4, "signature_moment": 4,
    "conversion_strength": 4, "copy_specificity": 5, "ai_house_style": 5,
}
WEAK = {
    "visual_thesis": 2, "hero_impact": 3, "imagery_art_direction": 2,
    "typography": 3, "color_system": 3, "layout_composition": 3,
    "whitespace_depth": 2, "motion_quality": 2, "signature_moment": 2,
    "conversion_strength": 3, "copy_specificity": 4, "ai_house_style": 2,
}


def test_loop_converges_by_consuming_the_brief() -> None:
    # The build's quality depends on CONSUMING the revision brief: every failing
    # category the build is told about gets "fixed" (scored 5) on the next round.
    # If the build ignored the brief (the v2 faked pattern), the loop could never
    # converge — so a pass here proves the brief actually drove the rebuild.
    fixed: set[str] = set()

    def build(i, brief):
        if brief is not None:
            fixed.update(brief.failing_categories)

    def judge(_):
        return [VisualScore(cat, 5 if cat in fixed else base, "note") for cat, base in WEAK.items()]

    result = run_design_loop(build=build, capture=lambda: SHOTS, judge=judge, max_iters=4)
    assert result.passed is True
    assert result.needs_signoff is True  # founder disposes, no auto-ship
    assert len(result.iterations) == 2
    assert result.iterations[0].passed is False
    assert fixed, "the revision brief was never consumed"
    # The originally-failing critical categories are exactly what the brief fixed.
    assert {"visual_thesis", "imagery_art_direction"} <= fixed


def test_loop_that_ignores_the_brief_plateaus() -> None:
    # A build that ignores the brief (the old faked pattern) never improves; plateau
    # detection halts it instead of spinning to the iteration cap.
    def build(i, brief):
        return None

    result = run_design_loop(
        build=build,
        capture=lambda: SHOTS,
        judge=lambda _: _scores(WEAK),
        max_iters=10,
        no_improve_patience=2,
    )
    assert result.passed is False
    assert result.halted_reason == "plateau"
    assert result.best is not None and result.best.overall < 80
    assert len(result.iterations) == 3  # i0 (best) + 2 stale rounds


def test_loop_branches_from_best_after_regression() -> None:
    # Monotonic acceptance: after a regression the next brief comes from the BEST
    # iteration, not the latest — so a bad round can't poison the revision chain.
    seqs = [
        {**STRONG, "imagery_art_direction": 3},  # one critical at 3 → fails, overall high
        {**WEAK, "visual_thesis": 1},  # big regression
        WEAK,
    ]
    counter = [0]
    seen_briefs: list[tuple[str, ...] | None] = []

    def judge(_):
        s = seqs[min(counter[0], len(seqs) - 1)]
        counter[0] += 1
        return _scores(s)

    def build(i, brief):
        seen_briefs.append(None if brief is None else tuple(sorted(brief.failing_categories)))

    result = run_design_loop(
        build=build, capture=lambda: SHOTS, judge=judge, max_iters=3, no_improve_patience=None
    )
    assert result.passed is False
    assert result.best_index == 0  # i0 is the highest-scoring build
    # After i1's regression, i2's brief is derived from i0 (the best), not i1.
    assert seen_briefs[2] == ("imagery_art_direction",)


def test_budget_halts_on_max_iters() -> None:
    guard = BudgetGuard(max_iters=2)
    built = [0]

    def build(i, brief):
        built[0] += 1

    result = run_design_loop(
        build=build,
        capture=lambda: SHOTS,
        judge=lambda _: _scores(WEAK),
        max_iters=10,
        budget=guard,
    )
    assert result.halted_reason == "budget_exhausted"
    assert built[0] == 2  # built twice, then the budget blocked the 3rd


def test_budget_halts_on_wall_clock() -> None:
    times = [0.0, 0.0, 5.0, 100.0]  # start, e0, e1, e2 (e2 exceeds the 10s budget)
    idx = [0]

    def clock() -> float:
        value = times[min(idx[0], len(times) - 1)]
        idx[0] += 1
        return value

    guard = BudgetGuard(max_seconds=10.0, clock=clock)
    result = run_design_loop(
        build=lambda i, b: None,
        capture=lambda: SHOTS,
        judge=lambda _: _scores(WEAK),
        max_iters=10,
        budget=guard,
    )
    assert result.halted_reason == "budget_exhausted"
    assert len(result.iterations) == 2


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
