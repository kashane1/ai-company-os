"""Quality loop with an independent judge — Phase 6 of the design engine.

The convergence engine: build -> shoot -> JUDGE -> (fail) revise -> repeat ->
(pass) await founder sign-off. The judge is a DIFFERENT model family from the
builder (Claude builds; Gemini vision scores) to neutralize self-preference bias,
and the rubric is used as a GATE, not a gradient the loop hill-climbs — so the
loop proposes, the founder disposes. On non-convergence it surfaces the
best-scoring iteration; a judge/build error degrades gracefully to the best so far.

This module is the pure, testable orchestrator: `build`, `judge`, and
`capture` are injected callables. The real Gemini-vision judge and the real build
step are wired in `scripts/agency/design_loop.py`; here they're abstract so the
control flow (termination, best-tracking, calibration, revision briefs) is fully
covered without a browser or an API.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from packages.web.design_studio import (
    VisualReviewReport,
    VisualScore,
    review_visual_quality,
)

# A judge maps screenshots -> category scores. MUST be a different model family
# from whatever produced the build.
Judge = Callable[[dict[str, str]], list[VisualScore]]
# A build step applies a revision brief (None on the first pass) and returns.
BuildStep = Callable[[int, "RevisionBrief | None"], None]
# Capture returns the screenshot paths for the current build.
Capture = Callable[[], dict[str, str]]


@dataclass(frozen=True)
class RevisionBrief:
    """What the loop hands the build/revise step when an iteration fails."""

    failing_categories: list[str]
    notes: dict[str, str]
    overall: int

    def to_dict(self) -> dict:
        return {
            "failing_categories": self.failing_categories,
            "notes": self.notes,
            "overall": self.overall,
        }


@dataclass
class BudgetGuard:
    """A cost ceiling for a long/unattended loop run.

    The orchestrator asks ``allows(index)`` before each build; once a cap is hit it
    halts and surfaces the best build so far (it never abandons work in progress).
    ``clock`` is injectable so wall-clock budgets are deterministically testable.
    """

    max_iters: int | None = None
    max_seconds: float | None = None
    clock: Callable[[], float] = time.monotonic
    _start: float | None = field(default=None, init=False, repr=False)

    def allows(self, index: int) -> bool:
        if self._start is None:
            self._start = self.clock()
        if self.max_iters is not None and index >= self.max_iters:
            return False
        if self.max_seconds is not None and (self.clock() - self._start) >= self.max_seconds:
            return False
        return True

    @property
    def reason(self) -> str:
        return "budget_exhausted"


@dataclass(frozen=True)
class Iteration:
    index: int
    overall: int
    passed: bool
    report: VisualReviewReport


@dataclass(frozen=True)
class LoopResult:
    passed: bool
    iterations: list[Iteration]
    best_index: int
    needs_signoff: bool
    halted_reason: str = ""

    @property
    def best(self) -> Iteration | None:
        return self.iterations[self.best_index] if self.iterations else None


def revision_brief(report: VisualReviewReport, floor: int = 4) -> RevisionBrief:
    """Turn a failed review into a targeted revision brief (the fix list)."""

    failing = [s.category for s in report.scores if s.score < floor]
    notes = {s.category: s.note for s in report.scores if s.score < floor}
    return RevisionBrief(failing_categories=failing, notes=notes, overall=report.overall)


def run_design_loop(
    *,
    build: BuildStep,
    capture: Capture,
    judge: Judge,
    max_iters: int = 4,
    no_improve_patience: int | None = None,
    budget: BudgetGuard | None = None,
    on_progress: Callable[[Iteration], None] | None = None,
) -> LoopResult:
    """Drive build -> capture -> judge -> revise until pass or a stop condition.

    Stop conditions, in order: a passing build (``needs_signoff=True`` — never
    auto-ships); ``budget`` exhausted; ``no_improve_patience`` consecutive rounds
    with no gain over the best so far (plateau detection — improvements plateau
    after 1-2 rounds, so polishing past that invites the judge inflating a build
    that isn't getting better); or the ``max_iters`` hard cap. On any of the
    non-pass exits the **best-scoring** iteration is surfaced. A build/judge/capture
    exception halts and degrades to the best result so far.

    The next revision brief is derived from the **best** iteration's report, not the
    latest — so a regression doesn't poison the chain (monotonic acceptance: the
    loop always branches from its best build).
    """

    iterations: list[Iteration] = []
    brief: RevisionBrief | None = None
    best: Iteration | None = None
    stale = 0

    for i in range(max_iters):
        if budget is not None and not budget.allows(i):
            return _result(iterations, passed=False, halted_reason=budget.reason)
        try:
            build(i, brief)
            screenshots = capture()
            scores = judge(screenshots)
        except Exception as exc:  # judge/build/capture failure → degrade
            reason = f"error: {type(exc).__name__}: {exc}"
            return _result(iterations, passed=False, halted_reason=reason)

        report = review_visual_quality(scores=scores, screenshots=screenshots)
        iteration = Iteration(index=i, overall=report.overall, passed=report.passed, report=report)
        iterations.append(iteration)
        if on_progress:
            on_progress(iteration)

        if report.passed:
            return _result(iterations, passed=True)

        if best is None or iteration.overall > best.overall:
            best, stale = iteration, 0
        else:
            stale += 1
            if no_improve_patience is not None and stale >= no_improve_patience:
                return _result(iterations, passed=False, halted_reason="plateau")

        brief = revision_brief(best.report)  # monotonic: branch from the best build

    return _result(iterations, passed=False, halted_reason="max_iters")


def _result(iterations: list[Iteration], *, passed: bool, halted_reason: str = "") -> LoopResult:
    best_index = (
        max(range(len(iterations)), key=lambda i: iterations[i].overall) if iterations else 0
    )
    return LoopResult(
        passed=passed,
        iterations=iterations,
        best_index=best_index,
        needs_signoff=passed,  # a pass still needs the founder to dispose
        halted_reason=halted_reason,
    )


# --------------------------------------------------------------------------- #
# Calibration harness — keep the judge honest against a gold-standard set.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GoldSample:
    """A known-good or known-bad build the judge must keep classifying correctly."""

    id: str
    screenshots: dict[str, str]
    expected: str  # "good" | "bad"


@dataclass(frozen=True)
class CalibrationReport:
    drifted: bool
    mismatches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"drifted": self.drifted, "mismatches": self.mismatches}


def calibrate(judge: Judge, gold: list[GoldSample]) -> CalibrationReport:
    """Re-score the gold set; if the judge mislabels known-good/known-bad it has
    drifted and the loop should halt rather than trust its scores."""

    mismatches: list[str] = []
    for sample in gold:
        report = review_visual_quality(
            scores=judge(sample.screenshots), screenshots=sample.screenshots
        )
        verdict = "good" if report.passed else "bad"
        if verdict != sample.expected:
            mismatches.append(f"{sample.id}: expected {sample.expected}, judged {verdict}")
    return CalibrationReport(drifted=bool(mismatches), mismatches=mismatches)
