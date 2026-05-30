"""Tests for the opportunity scorer + the advancement gate policy.

Verifies the worked example in docs/founder/opportunity-scorecard.md (score 71)
and the hard gates / thresholds.
"""

from __future__ import annotations

import pytest

from packages.discovery.scoring import (
    ConfidenceModel,
    ScoringConfig,
    compute_confidence,
    compute_score,
    load_scoring_config,
)
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.policies.discovery_gates import (
    assert_ready_to_build,
    evaluate_opportunity,
    score_opportunity_record,
)
from packages.schemas.experiment import (
    ExperimentMetric,
    ExperimentRecord,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)
from packages.schemas.opportunity import (
    ComplianceFlag,
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunitySignals,
    OpportunityStatus,
    SourceRef,
)

# The Etsy-photo-resize example from the scorecard doc.
ETSY = OpportunitySignals(
    search_volume=5,
    buyer_intent=7,
    urgency=6,
    willingness_to_pay=7,
    competition_weakness=6,
    community_pain=8,
    repeated_workflow=9,
    distribution_path=7,
    expected_margin=8,
    build_feasibility=8,
    defensibility=3,
    risk=9,
)


@pytest.fixture
def config() -> ScoringConfig:
    # Load the real shipped config so the test guards the YAML too.
    return load_scoring_config()


def test_worked_example_scores_about_71(config: ScoringConfig) -> None:
    score = compute_score(ETSY, config.weights)
    assert abs(score - 71) < 1, f"expected ~71, got {score:.2f}"


def test_signals_clamped_to_0_10(config: ScoringConfig) -> None:
    over = OpportunitySignals(buyer_intent=99)
    under = OpportunitySignals(buyer_intent=-5)
    # Out-of-range values are clamped, so a single maxed signal can't exceed
    # the normalized ceiling implied by its weight share.
    assert compute_score(over, config.weights) <= 100
    assert compute_score(under, config.weights) >= 0


def test_zero_weights_yield_zero_score() -> None:
    assert compute_score(ETSY, {}) == 0.0


def test_confidence_rewards_evidence_and_diversity() -> None:
    model = ConfidenceModel(target_evidence=5, diversity_bonus=True)
    strong = compute_confidence(5, 3, model)
    weak = compute_confidence(1, 1, model)
    assert strong >= 0.6
    assert weak < 0.6  # one source = hypothesis, not actionable


def test_confidence_without_diversity_bonus_is_just_base() -> None:
    model = ConfidenceModel(target_evidence=5, diversity_bonus=False)
    assert compute_confidence(5, 1, model) == 1.0


def test_strong_well_evidenced_wedge_advances(config: ScoringConfig) -> None:
    decision = evaluate_opportunity(
        ETSY, evidence_links=5, distinct_sources=3, config=config
    )
    assert decision.advance is True
    assert decision.confidence >= 0.6
    assert decision.reasons == []


def test_high_score_one_source_is_hypothesis(config: ScoringConfig) -> None:
    decision = evaluate_opportunity(
        ETSY, evidence_links=1, distinct_sources=1, config=config
    )
    assert decision.advance is False
    assert PolicyViolationCode.DISCOVERY_LOW_CONFIDENCE.value in decision.reason_codes


def test_high_risk_is_a_hard_gate_not_a_low_score(config: ScoringConfig) -> None:
    risky = OpportunitySignals(**{**ETSY.to_dict(), "risk": 1})
    decision = evaluate_opportunity(risky, evidence_links=5, distinct_sources=3, config=config)
    assert decision.advance is False
    assert PolicyViolationCode.DISCOVERY_RISK_TOO_HIGH.value in decision.reason_codes


def test_blocked_compliance_flag_stops_advancement(config: ScoringConfig) -> None:
    decision = evaluate_opportunity(
        ETSY,
        evidence_links=5,
        distinct_sources=3,
        compliance_flags=[ComplianceFlag.REGULATED_DATA],
        config=config,
    )
    assert decision.advance is False
    assert PolicyViolationCode.DISCOVERY_BLOCKED_COMPLIANCE_FLAG.value in decision.reason_codes


def test_no_distribution_blocks_advancement(config: ScoringConfig) -> None:
    no_dist = OpportunitySignals(**{**ETSY.to_dict(), "distribution_path": 0})
    decision = evaluate_opportunity(no_dist, evidence_links=5, distinct_sources=3, config=config)
    assert decision.advance is False
    assert PolicyViolationCode.DISCOVERY_NO_DISTRIBUTION.value in decision.reason_codes


def test_score_opportunity_record_sets_status(config: ScoringConfig) -> None:
    record = OpportunityRecord(
        id="opp_1",
        title="t",
        problem="p",
        audience="a",
        source=SourceRef(connector="hackernews"),
        signals=ETSY,
        evidence=[
            EvidenceLink(url="https://news.ycombinator.com/item?id=1", kind=EvidenceKind.REQUEST),
            EvidenceLink(url="https://www.reddit.com/r/Etsy/1", kind=EvidenceKind.COMPLAINT),
            EvidenceLink(url="https://example.com/forum/3", kind=EvidenceKind.COMPLAINT),
            EvidenceLink(url="https://example.com/forum/4", kind=EvidenceKind.REVIEW),
            EvidenceLink(url="https://example.org/5", kind=EvidenceKind.REVIEW),
        ],
    )
    decision, scored = score_opportunity_record(record, config)
    assert scored.score == decision.score
    assert scored.status in (OpportunityStatus.VALIDATING, OpportunityStatus.SCORED)
    if decision.advance:
        assert scored.status is OpportunityStatus.VALIDATING


def _experiment(status: ExperimentStatus) -> ExperimentRecord:
    return ExperimentRecord(
        id="exp_1",
        opportunity_id="opp_1",
        type=ExperimentType.WAITLIST,
        hypothesis="people will sign up",
        success_criteria=SuccessCriteria(
            metric=ExperimentMetric.SIGNUPS, threshold=50, window="7d"
        ),
        status=status,
    )


def _opportunity() -> OpportunityRecord:
    return OpportunityRecord(
        id="opp_1", title="t", problem="p", audience="a", source=SourceRef(connector="hackernews")
    )


def test_build_gate_allows_passed_experiment() -> None:
    assert_ready_to_build(_opportunity(), _experiment(ExperimentStatus.PASSED))  # no raise


def test_build_gate_blocks_missing_experiment() -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_ready_to_build(_opportunity(), None)
    assert exc.value.code == PolicyViolationCode.DISCOVERY_EXPERIMENT_NOT_PASSED.value


def test_build_gate_blocks_unpassed_experiment() -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_ready_to_build(_opportunity(), _experiment(ExperimentStatus.RUNNING))
    assert exc.value.code == PolicyViolationCode.DISCOVERY_EXPERIMENT_NOT_PASSED.value
