"""Tests for the scoring pass — orchestration with a deterministic stub provider.

No LLM: the SignalProvider is a stub so the test asserts ranking, advance/held/
skipped accounting, persistence, and the markdown render without any non-
determinism.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.discovery.connectors.base import RawSignal
from packages.discovery.inbox import OpportunityInbox
from packages.discovery.scoring import load_scoring_config
from packages.discovery.scoring_pass import ScoringPass
from packages.schemas.opportunity import (
    EvidenceKind,
    OpportunityRecord,
    OpportunitySignals,
    OpportunityStatus,
)

STRONG = OpportunitySignals(
    search_volume=5, buyer_intent=7, urgency=6, willingness_to_pay=7,
    competition_weakness=6, community_pain=8, repeated_workflow=9,
    distribution_path=7, expected_margin=8, build_feasibility=8,
    defensibility=3, risk=9,
)
WEAK = OpportunitySignals(
    search_volume=2, buyer_intent=2, urgency=2, willingness_to_pay=2,
    competition_weakness=2, community_pain=2, repeated_workflow=2,
    distribution_path=2, expected_margin=2, build_feasibility=2,
    defensibility=2, risk=9,
)


def _inbox(tmp_path: Path) -> OpportunityInbox:
    fixed = datetime(2026, 5, 29, tzinfo=timezone.utc)
    return OpportunityInbox(root=tmp_path / "opportunities", now=lambda: fixed)


def _signal(url: str, text: str) -> RawSignal:
    return RawSignal(text=text, url=url, kind=EvidenceKind.REQUEST, quote=text)


def _seed_strong_with_evidence(inbox: OpportunityInbox) -> str:
    text = "Is there a tool that automates marketplace photo resizing"
    inbox.ingest_signals(
        "hackernews", "resize", [_signal("https://news.ycombinator.com/item?id=1", text)]
    )
    # Add 4 more distinct-source evidence links so confidence can clear the gate.
    record = [r for r in inbox.list() if r.title.startswith("Is there")][0]
    payload = record.to_dict()
    payload["evidence"] = [
        {"url": "https://news.ycombinator.com/item?id=1", "kind": "request"},
        {"url": "https://www.reddit.com/r/Etsy/1", "kind": "complaint"},
        {"url": "https://etsy-forum.example/2", "kind": "complaint"},
        {"url": "https://reviews.example/3", "kind": "review"},
        {"url": "https://reviews.example/4", "kind": "willingness-to-pay"},
    ]
    inbox.save(OpportunityRecord.from_dict(payload))
    return record.id


def test_pass_ranks_and_advances_strong_wedge(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    strong_id = _seed_strong_with_evidence(inbox)
    inbox.ingest_signals(
        "hackernews", "q",
        [_signal("https://news.ycombinator.com/item?id=9", "I hate doing taxes manually")],
    )

    def provider(record: OpportunityRecord) -> OpportunitySignals:
        return STRONG if record.id == strong_id else WEAK

    report = ScoringPass(inbox, config=load_scoring_config(), signal_provider=provider).run()

    assert len(report.scored) == 2
    assert report.scored[0].record.id == strong_id  # highest score ranked first
    assert report.advanced == 1
    assert report.held == 1
    assert report.skipped_no_signals == 0


def test_pass_persists_scored_status(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    strong_id = _seed_strong_with_evidence(inbox)
    ScoringPass(inbox, signal_provider=lambda r: STRONG).run()

    reloaded = inbox.get(strong_id)
    assert reloaded.score is not None
    assert reloaded.status is OpportunityStatus.VALIDATING  # cleared the gate


def test_pass_skips_when_no_signals_available(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    inbox.ingest_signals(
        "hackernews", "q",
        [_signal("https://news.ycombinator.com/item?id=1", "Is there a tool for X")],
    )

    # Provider returns None => not enough evidence to score; leave it in the inbox.
    report = ScoringPass(inbox, signal_provider=lambda r: None).run()
    assert report.skipped_no_signals == 1
    assert report.scored == []
    assert inbox.list()[0].status is OpportunityStatus.INBOX  # untouched


def test_pass_only_processes_inbox_status(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    strong_id = _seed_strong_with_evidence(inbox)
    # First pass scores it (status leaves INBOX); second pass must skip it.
    ScoringPass(inbox, signal_provider=lambda r: STRONG).run()
    report2 = ScoringPass(inbox, signal_provider=lambda r: STRONG).run()
    assert report2.scored == []
    assert inbox.get(strong_id).status is not OpportunityStatus.INBOX


def test_pass_respects_limit(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    for i in range(3):
        inbox.ingest_signals(
            "hackernews", "q",
            [_signal(f"https://news.ycombinator.com/item?id={i}", f"Is there a tool number {i}")],
        )
    report = ScoringPass(inbox, signal_provider=lambda r: WEAK).run(limit=2)
    assert len(report.scored) == 2


def test_report_markdown_renders_table(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    _seed_strong_with_evidence(inbox)
    report = ScoringPass(inbox, signal_provider=lambda r: STRONG).run()
    md = report.to_markdown()
    assert "# Opportunity scoring pass" in md
    assert "| # | Score | Conf | Advance | Title | Top reason |" in md
    assert "advanced" in md
