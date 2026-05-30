"""Tests for the heuristic analyst — deterministic baseline signal scoring."""

from __future__ import annotations

from packages.discovery.analyst import HeuristicSignalProvider, heuristic_signals
from packages.schemas.opportunity import (
    ComplianceFlag,
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    SourceRef,
)


def _record(*evidence: EvidenceLink, flags=None) -> OpportunityRecord:
    return OpportunityRecord(
        id="opp_1",
        title="Is there a tool that automates invoicing",
        problem="I do this manually every month and hate it",
        audience="freelancers",
        source=SourceRef(connector="hackernews"),
        evidence=list(evidence),
        compliance_flags=flags or [],
    )


def test_no_evidence_returns_none() -> None:
    assert heuristic_signals(_record()) is None


def test_signals_are_within_range() -> None:
    signals = heuristic_signals(
        _record(
            EvidenceLink(url="https://news.ycombinator.com/item?id=1", kind=EvidenceKind.REQUEST),
            EvidenceLink(url="https://www.reddit.com/r/freelance/2", kind=EvidenceKind.COMPLAINT),
        )
    )
    assert signals is not None
    for value in signals.to_dict().values():
        assert 0.0 <= float(value) <= 10.0


def test_willingness_to_pay_evidence_raises_that_signal() -> None:
    low = heuristic_signals(
        _record(EvidenceLink(url="https://a.example/1", kind=EvidenceKind.OTHER))
    )
    high = heuristic_signals(
        _record(EvidenceLink(url="https://a.example/1", kind=EvidenceKind.WILLINGNESS_TO_PAY))
    )
    assert high.willingness_to_pay > low.willingness_to_pay


def test_tos_risk_flag_drives_risk_low_to_trip_hard_gate() -> None:
    signals = heuristic_signals(
        _record(
            EvidenceLink(url="https://a.example/1", kind=EvidenceKind.REQUEST),
            flags=[ComplianceFlag.TOS_RISK],
        )
    )
    assert signals.risk <= 2  # low risk score == high real risk -> hard gate


def test_clean_opportunity_is_low_risk() -> None:
    signals = heuristic_signals(
        _record(EvidenceLink(url="https://a.example/1", kind=EvidenceKind.REQUEST))
    )
    assert signals.risk >= 8


def test_provider_is_callable() -> None:
    provider = HeuristicSignalProvider()
    record = _record(EvidenceLink(url="https://a.example/1", kind=EvidenceKind.REQUEST))
    assert provider(record) == heuristic_signals(record)
    assert provider(_record()) is None


def test_deterministic() -> None:
    record = _record(
        EvidenceLink(url="https://news.ycombinator.com/item?id=1", kind=EvidenceKind.WORKAROUND)
    )
    assert heuristic_signals(record) == heuristic_signals(record)
