"""Analyst calibration eval — keep scoring honest as prompts/weights change.

Now that a real ``LLMSignalProvider`` exists, the scoring is only as trustworthy
as it is *calibrated*: a labelled wedge that should clearly advance must score
high, and an obvious dud must not. This module runs any ``SignalProvider`` over a
set of labelled cases and reports how often the outcome lands in the expected
band — a regression signal you can run whenever the prompt, weights, or
heuristics change.

It is provider-agnostic on purpose: run it against the deterministic
``HeuristicSignalProvider`` in CI (no network, no flake) to catch scoring/weight
drift, and against a live ``LLMSignalProvider`` ad hoc to sanity-check the model.

A ``CalibrationCase`` labels the *expected outcome*, not exact numbers — scoring
is a judgement, so we assert bands ("should advance", "score >= 65"), never
brittle equality.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.discovery.scoring import ScoringConfig, load_scoring_config
from packages.discovery.scoring_pass import SignalProvider
from packages.policies.discovery_gates import evaluate_opportunity
from packages.schemas.opportunity import (
    ComplianceFlag,
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunitySignals,
    SourceRef,
)


@dataclass(frozen=True)
class CalibrationCase:
    """One labelled wedge and what we expect the scorer to conclude."""

    name: str
    record: OpportunityRecord
    expect_advance: bool
    min_score: float | None = None
    max_score: float | None = None


@dataclass(frozen=True)
class CaseResult:
    name: str
    passed: bool
    score: float
    confidence: float
    advance: bool
    detail: str


@dataclass(frozen=True)
class CalibrationReport:
    results: list[CaseResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def accuracy(self) -> float:
        return round(self.passed / self.total, 4) if self.total else 0.0

    @property
    def failures(self) -> list[CaseResult]:
        return [result for result in self.results if not result.passed]

    def to_markdown(self) -> str:
        lines = [
            "# Analyst calibration",
            "",
            f"- cases: **{self.total}** · passed: **{self.passed}** "
            f"· accuracy: **{self.accuracy:.0%}**",
            "",
            "| Case | OK | Score | Conf | Advance | Detail |",
            "|------|:--:|------:|-----:|:-------:|--------|",
        ]
        for result in self.results:
            ok = "✅" if result.passed else "❌"
            advance = "yes" if result.advance else "no"
            lines.append(
                f"| {result.name} | {ok} | {result.score:.0f} | {result.confidence:.2f} "
                f"| {advance} | {result.detail} |"
            )
        return "\n".join(lines) + "\n"


def evaluate_case(
    case: CalibrationCase,
    provider: SignalProvider,
    config: ScoringConfig,
) -> CaseResult:
    signals = case.record.signals or provider(case.record)
    if signals is None:
        # The provider declined to score (insufficient evidence). That only
        # matches a case expecting "do not advance".
        passed = case.expect_advance is False
        detail = "provider returned no signals (insufficient evidence)"
        return CaseResult(case.name, passed, 0.0, 0.0, False, detail)

    decision = evaluate_opportunity(
        signals,
        evidence_links=len(case.record.evidence),
        distinct_sources=max(1, case.record.distinct_sources()),
        compliance_flags=case.record.compliance_flags,
        config=config,
    )

    checks: list[str] = []
    ok = True
    if decision.advance != case.expect_advance:
        ok = False
        checks.append(f"expected advance={case.expect_advance}, got {decision.advance}")
    if case.min_score is not None and decision.score < case.min_score:
        ok = False
        checks.append(f"score {decision.score:.0f} < min {case.min_score:g}")
    if case.max_score is not None and decision.score > case.max_score:
        ok = False
        checks.append(f"score {decision.score:.0f} > max {case.max_score:g}")
    detail = "ok" if ok else "; ".join(checks)
    return CaseResult(
        case.name, ok, decision.score, decision.confidence, decision.advance, detail
    )


def run_calibration(
    cases: list[CalibrationCase],
    provider: SignalProvider,
    *,
    config: ScoringConfig | None = None,
) -> CalibrationReport:
    """Run every case through ``provider`` + the validate gate; report pass rate."""
    cfg = config or load_scoring_config()
    return CalibrationReport(results=[evaluate_case(case, provider, cfg) for case in cases])


# ── Canonical labelled dataset ──────────────────────────────────────────────────
#
# Deterministic by construction: the gate-calibration cases carry explicit
# signals (so they exercise the weights + thresholds regardless of provider and
# catch *weight/threshold drift*), while the provider-calibration cases carry no
# signals (so they exercise whatever SignalProvider is under test). Run against
# HeuristicSignalProvider this set should be 100% — a CI tripwire for drift.

_STRONG = OpportunitySignals(
    search_volume=5, buyer_intent=7, urgency=6, willingness_to_pay=7,
    competition_weakness=6, community_pain=8, repeated_workflow=9,
    distribution_path=7, expected_margin=8, build_feasibility=8,
    defensibility=3, risk=9,
)


def _evidence(n: int) -> list[EvidenceLink]:
    hosts = ["news.ycombinator.com", "www.reddit.com", "forum.example", "rev.example", "x.example"]
    return [
        EvidenceLink(url=f"https://{hosts[i % len(hosts)]}/{i}", kind=EvidenceKind.REQUEST)
        for i in range(n)
    ]


def _case_record(
    rec_id: str,
    *,
    signals: OpportunitySignals | None,
    evidence: int,
    flags: list[ComplianceFlag] | None = None,
) -> OpportunityRecord:
    return OpportunityRecord(
        id=rec_id,
        title="Is there a tool that automates this recurring manual task",
        problem="People do this by hand repeatedly and complain about it.",
        audience="a specific, reachable audience",
        source=SourceRef(connector="hackernews", query="automate"),
        evidence=_evidence(evidence),
        signals=signals,
        compliance_flags=flags or [],
    )


def default_calibration_cases() -> list[CalibrationCase]:
    return [
        # Gate calibration (explicit signals): strong, well-evidenced -> advances.
        CalibrationCase(
            name="strong_wedge_advances",
            record=_case_record("opp_strong", signals=_STRONG, evidence=5),
            expect_advance=True,
            min_score=65,
        ),
        # High ToS/regulatory risk is a hard gate, never advances.
        CalibrationCase(
            name="tos_risk_blocked",
            record=_case_record(
                "opp_tos",
                signals=OpportunitySignals(**{**_STRONG.to_dict(), "risk": 1}),
                evidence=5,
                flags=[ComplianceFlag.TOS_RISK],
            ),
            expect_advance=False,
        ),
        # No distribution path is a hard gate.
        CalibrationCase(
            name="no_distribution_blocked",
            record=_case_record(
                "opp_nodist",
                signals=OpportunitySignals(**{**_STRONG.to_dict(), "distribution_path": 0}),
                evidence=5,
            ),
            expect_advance=False,
        ),
        # Strong signals but a single source -> low confidence, stays a hypothesis.
        CalibrationCase(
            name="thin_evidence_blocked",
            record=_case_record("opp_thin", signals=_STRONG, evidence=1),
            expect_advance=False,
        ),
        # Provider calibration (no signals): a weakly-evidenced wedge the provider
        # must not push through.
        CalibrationCase(
            name="weak_wedge_not_advanced",
            record=_case_record("opp_weak", signals=None, evidence=1),
            expect_advance=False,
        ),
    ]
