"""Round-trip tests for the discovery schemas (opportunity, experiment, dossier).

Every record must survive ``to_dict`` -> ``from_dict`` unchanged so it can be
persisted as JSON and reloaded without loss.
"""

from __future__ import annotations

from packages.schemas.dossier import (
    DossierAudience,
    DossierChannel,
    DossierMonetization,
    DossierMvp,
    DossierRecord,
    MonetizationModel,
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


def _sample_opportunity() -> OpportunityRecord:
    return OpportunityRecord(
        id="opp_test",
        title="Etsy sellers manually resize product photos",
        problem="Sellers resize photos for each marketplace by hand.",
        audience="Etsy sellers with >100 SKUs",
        source=SourceRef(connector="hackernews", query="resize product photos"),
        status=OpportunityStatus.INBOX,
        evidence=[
            EvidenceLink(
                url="https://news.ycombinator.com/item?id=1",
                kind=EvidenceKind.REQUEST,
                quote="is there a tool that resizes for each marketplace",
                captured_at="2026-05-29T00:00:00+00:00",
            ),
            EvidenceLink(
                url="https://www.reddit.com/r/Etsy/comments/abc", kind=EvidenceKind.COMPLAINT
            ),
        ],
        signals=OpportunitySignals(buyer_intent=7, distribution_path=7, risk=9),
        score=71.0,
        confidence=0.9,
        compliance_flags=[ComplianceFlag.NEEDS_REVIEW],
        distribution_ideas=["r/Etsy", "Etsy seller forums"],
        next_actions=["score signals", "draft landing page"],
    )


def test_opportunity_round_trip() -> None:
    record = _sample_opportunity()
    restored = OpportunityRecord.from_dict(record.to_dict())
    assert restored == record


def test_opportunity_distinct_sources_counts_hosts() -> None:
    record = _sample_opportunity()
    # news.ycombinator.com + reddit.com (www stripped) == 2 distinct hosts.
    assert record.distinct_sources() == 2


def test_opportunity_signals_from_dict_defaults_missing_to_zero() -> None:
    signals = OpportunitySignals.from_dict({"buyer_intent": 8})
    assert signals.buyer_intent == 8.0
    assert signals.search_volume == 0.0


def test_experiment_round_trip() -> None:
    record = ExperimentRecord(
        id="exp_1",
        opportunity_id="opp_test",
        type=ExperimentType.WAITLIST,
        hypothesis="Etsy sellers will join a waitlist for auto-resize.",
        success_criteria=SuccessCriteria(
            metric=ExperimentMetric.SIGNUPS, threshold=50, window="7 days"
        ),
        status=ExperimentStatus.PLANNED,
    )
    restored = ExperimentRecord.from_dict(record.to_dict())
    assert restored == record
    assert restored.success_criteria.threshold == 50


def test_dossier_round_trip() -> None:
    record = DossierRecord(
        id="dos_1",
        opportunity_id="opp_test",
        summary="Auto-resize product photos for every marketplace.",
        audience=DossierAudience(who="Etsy sellers", size="~2M", where_they_are=["r/Etsy"]),
        pain_quotes=["I hate doing this by hand"],
        mvp=DossierMvp(
            thinnest_slice="Upload one photo, get all sizes",
            build_kit="saas",
            estimated_build_days=5,
        ),
        monetization=DossierMonetization(
            model=MonetizationModel.SUBSCRIPTION, price_point="$19/mo"
        ),
        distribution=[
            DossierChannel(
                channel="r/Etsy",
                approach="be useful first",
                compliance="subreddit self-promo rules",
            )
        ],
        risks=["thin defensibility"],
    )
    restored = DossierRecord.from_dict(record.to_dict())
    assert restored == record
