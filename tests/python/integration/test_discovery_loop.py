"""Integration test for the discovery loop: run → score → gate → handoff.

Exercises the pieces together with stub connectors, the heuristic analyst, and a
capturing goal sink — including a mid-run stop and the build gate blocking a
handoff until an experiment passes. Fully offline and deterministic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from packages.discovery.analyst import HeuristicSignalProvider
from packages.discovery.connectors.base import ConnectorConfig, FetchOptions, RawSignal
from packages.discovery.handoff import guard_and_handoff, opportunity_to_goal
from packages.discovery.inbox import OpportunityInbox
from packages.discovery.run import DiscoveryRunStatus, run_discovery
from packages.discovery.scoring_pass import ScoringPass
from packages.policies.approvals import PolicyViolation
from packages.schemas.experiment import (
    ExperimentMetric,
    ExperimentRecord,
    ExperimentStatus,
    ExperimentType,
    SuccessCriteria,
)
from packages.schemas.goal import GoalRecord
from packages.schemas.opportunity import EvidenceKind, OpportunityStatus

FIXED = datetime(2026, 5, 29, tzinfo=timezone.utc)


class StubConnector:
    def __init__(self, cid: str, signals: list[RawSignal]) -> None:
        self.id = cid
        self.config = ConnectorConfig(id=cid)
        self._signals = signals

    def fetch(self, options: FetchOptions) -> list[RawSignal]:
        return self._signals

    def healthcheck(self) -> tuple[bool, str]:
        return (True, "")


def _sig(url: str, text: str, kind: EvidenceKind = EvidenceKind.REQUEST) -> RawSignal:
    return RawSignal(text=text, url=url, kind=kind, quote=text)


def _inbox(tmp_path: Path) -> OpportunityInbox:
    return OpportunityInbox(root=tmp_path / "opportunities", now=lambda: FIXED)


def test_full_loop_run_score_gate_handoff(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    # A wedge with rich, multi-source evidence so it can clear the gate.
    strong = [
        _sig("https://news.ycombinator.com/item?id=1", "Is there a tool to automate invoicing"),
        _sig("https://www.reddit.com/r/freelance/2", "I hate invoices", EvidenceKind.COMPLAINT),
        _sig("https://forum.example/3", "anyone know an app for invoicing", EvidenceKind.REQUEST),
        _sig("https://reviews.example/4", "I'd pay for this", EvidenceKind.WILLINGNESS_TO_PAY),
        _sig("https://reviews.example/5", "current tools are terrible", EvidenceKind.REVIEW),
    ]
    connectors = {"hackernews": StubConnector("hackernews", strong)}

    # 1. RUN — fills the inbox.
    report = run_discovery(
        inbox=inbox, connectors=connectors, queries=["invoicing"], now=lambda: FIXED
    )
    assert report.status == DiscoveryRunStatus.COMPLETED
    assert report.signals_ingested == 5
    assert len(inbox.list()) == 5

    # 2. SCORE — heuristic analyst fills signals, scoring pass ranks + gates.
    scoring = ScoringPass(inbox, signal_provider=HeuristicSignalProvider())
    pass_report = scoring.run()
    assert pass_report.skipped_no_signals == 0
    assert len(pass_report.scored) == 5

    # Pick the top-ranked opportunity for the gate/handoff steps.
    top = pass_report.scored[0].record

    # 3. GATE — handoff is blocked until a validation experiment passes.
    goals: list[GoalRecord] = []
    experiment = ExperimentRecord(
        id="exp_1",
        opportunity_id=top.id,
        type=ExperimentType.WAITLIST,
        hypothesis="people sign up",
        success_criteria=SuccessCriteria(
            metric=ExperimentMetric.SIGNUPS, threshold=50, window="7d"
        ),
        status=ExperimentStatus.RUNNING,
    )
    with pytest.raises(PolicyViolation):
        guard_and_handoff(top, experiment, sink=goals.append, now=lambda: FIXED)
    assert goals == []  # nothing created while the gate is closed

    # 4. HANDOFF — once the experiment passes, the opportunity becomes a goal.
    passed = ExperimentRecord.from_dict({**experiment.to_dict(), "status": "passed"})
    goal = guard_and_handoff(top, passed, sink=goals.append, now=lambda: FIXED)
    assert goals == [goal]
    assert goal.id.startswith("goal_")
    assert goal.summary == top.problem


def test_mid_run_stop_halts_sweep(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    connectors = {
        "a": StubConnector("a", [_sig("https://a/1", "tool one")]),
        "b": StubConnector("b", [_sig("https://b/1", "tool two")]),
    }
    calls = {"n": 0}

    def should_stop() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    report = run_discovery(
        inbox=inbox, connectors=connectors, queries=["q"],
        should_stop=should_stop, now=lambda: FIXED,
    )
    assert report.stopped_early is True
    assert report.signals_ingested == 1


def test_opportunity_to_goal_projection(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    [record] = inbox.ingest_signals(
        "hackernews", "q", [_sig("https://news.ycombinator.com/item?id=1", "Is there a tool for X")]
    )
    goal = opportunity_to_goal(record, now=lambda: FIXED)
    assert goal.id == f"goal_{record.id.removeprefix('opp_')}"
    assert record.status is OpportunityStatus.INBOX  # projection doesn't mutate the record
