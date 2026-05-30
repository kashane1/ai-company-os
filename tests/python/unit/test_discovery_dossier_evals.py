"""Tests for the dossier generator (A4) and discovery metrics (A6)."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.discovery.dossier import build_dossier
from packages.discovery.evals import compute_metrics, source_yield
from packages.schemas.experiment import (
    ExperimentMetric,
    ExperimentRecord,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)
from packages.schemas.opportunity import (
    Competitor,
    ComplianceFlag,
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunityStatus,
    SourceRef,
)

FIXED = datetime(2026, 5, 29, tzinfo=timezone.utc)


def _opportunity(**overrides) -> OpportunityRecord:
    base = dict(
        id="opp_abc",
        title="Etsy resize",
        problem="Sellers resize photos by hand.",
        audience="Etsy sellers",
        source=SourceRef(connector="hackernews", query="resize"),
        status=OpportunityStatus.VALIDATING,
        evidence=[
            EvidenceLink(
                url="https://news.ycombinator.com/item?id=1",
                kind=EvidenceKind.REQUEST,
                quote="is there a tool",
            ),
        ],
        competitors=[
            Competitor(name="PhotoBulk", pricing="$10", weakness="no marketplace presets")
        ],
        mvp_idea="Upload once, export all marketplace sizes",
        distribution_ideas=["r/Etsy", "Etsy forums"],
    )
    base.update(overrides)
    return OpportunityRecord(**base)


def test_build_dossier_projects_core_fields() -> None:
    dossier = build_dossier(_opportunity(), now=lambda: FIXED)
    assert dossier.id == "dos_abc"
    assert dossier.opportunity_id == "opp_abc"
    assert dossier.audience.who == "Etsy sellers"
    assert dossier.pain_quotes == ["is there a tool"]
    assert dossier.competitors[0].weaknesses == ["no marketplace presets"]
    assert dossier.mvp.thinnest_slice == "Upload once, export all marketplace sizes"
    assert [c.channel for c in dossier.distribution] == ["r/Etsy", "Etsy forums"]


def test_dossier_flags_missing_experiment() -> None:
    dossier = build_dossier(_opportunity(), None, now=lambda: FIXED)
    assert any("No validation experiment" in q for q in dossier.open_questions)


def test_dossier_flags_unpassed_experiment() -> None:
    exp = ExperimentRecord(
        id="exp_1",
        opportunity_id="opp_abc",
        type=ExperimentType.WAITLIST,
        hypothesis="x",
        success_criteria=SuccessCriteria(metric=ExperimentMetric.SIGNUPS, threshold=50),
        status=ExperimentStatus.RUNNING,
    )
    dossier = build_dossier(_opportunity(), exp, now=lambda: FIXED)
    assert any("not passed" in q for q in dossier.open_questions)


def test_dossier_surfaces_compliance_flags_as_risks() -> None:
    opp = _opportunity(compliance_flags=[ComplianceFlag.PII])
    dossier = build_dossier(opp, now=lambda: FIXED)
    assert any("pii" in risk for risk in dossier.risks)


def test_metrics_funnel_and_validation_rate() -> None:
    records = [
        _opportunity(id="opp_1", status=OpportunityStatus.INBOX),
        _opportunity(id="opp_2", status=OpportunityStatus.VALIDATED),
        _opportunity(id="opp_3", status=OpportunityStatus.SHIPPED),
        _opportunity(id="opp_4", status=OpportunityStatus.KILLED),
    ]
    metrics = compute_metrics(records)
    assert metrics.total == 4
    assert metrics.validated == 2  # validated + shipped count as validated
    assert metrics.shipped == 1
    assert metrics.killed == 1
    assert metrics.validation_rate == 0.5
    assert "discovery metrics" in metrics.to_markdown().lower()


def test_source_yield_per_connector() -> None:
    records = [
        _opportunity(
            id="opp_1", source=SourceRef(connector="hackernews"),
            status=OpportunityStatus.VALIDATED,
        ),
        _opportunity(
            id="opp_2", source=SourceRef(connector="hackernews"),
            status=OpportunityStatus.INBOX,
        ),
        _opportunity(
            id="opp_3", source=SourceRef(connector="github"), status=OpportunityStatus.INBOX
        ),
    ]
    by_connector = {item.connector: item for item in source_yield(records)}
    assert by_connector["hackernews"].found == 2
    assert by_connector["hackernews"].validated == 1
    assert by_connector["hackernews"].yield_ratio == 0.5
    assert by_connector["github"].yield_ratio == 0.0
