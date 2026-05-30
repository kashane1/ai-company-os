"""Tests for the opportunity inbox — drafting, dedup, and persistence.

Uses a tmp_path root so nothing touches the real runtime state tree.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.discovery.connectors.base import RawSignal
from packages.discovery.inbox import OpportunityInbox, opportunity_id_for
from packages.schemas.opportunity import EvidenceKind, OpportunityStatus


def _inbox(tmp_path: Path) -> OpportunityInbox:
    fixed = datetime(2026, 5, 29, tzinfo=timezone.utc)
    return OpportunityInbox(root=tmp_path / "opportunities", now=lambda: fixed)


def _signal(url: str, text: str = "Is there a tool that automates X") -> RawSignal:
    return RawSignal(text=text, url=url, kind=EvidenceKind.REQUEST, quote=text)


def test_draft_from_signal_sets_inbox_status(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    record = inbox.draft_from_signal(
        _signal("https://news.ycombinator.com/item?id=1"), "hackernews", query="x"
    )
    assert record.status is OpportunityStatus.INBOX
    assert record.source.connector == "hackernews"
    assert len(record.evidence) == 1


def test_deterministic_id_from_title() -> None:
    a = opportunity_id_for("Is there a tool that automates X")
    b = opportunity_id_for("is there a   tool that automates x!!!")  # normalized the same
    assert a == b


def test_ingest_dedupes_same_pain_merges_evidence(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    text = "Is there a tool that automates invoicing"
    inbox.ingest_signals(
        "hackernews", "invoicing", [_signal("https://news.ycombinator.com/item?id=1", text)]
    )
    # Same pain, different evidence URL on a later run -> merges, not duplicates.
    inbox.ingest_signals(
        "github", "invoicing", [_signal("https://github.com/acme/repo/issues/2", text)]
    )

    records = inbox.list()
    assert len(records) == 1
    assert len(records[0].evidence) == 2


def test_ingest_same_url_does_not_double_count(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    text = "Is there a tool that automates invoicing"
    url = "https://news.ycombinator.com/item?id=1"
    inbox.ingest_signals("hackernews", "q", [_signal(url, text)])
    inbox.ingest_signals("hackernews", "q", [_signal(url, text)])
    records = inbox.list()
    assert len(records) == 1
    assert len(records[0].evidence) == 1


def test_ingest_skips_empty_signals(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    stored = inbox.ingest_signals("hackernews", "q", [RawSignal(text="", url="")])
    assert stored == []
    assert inbox.list() == []


def test_get_and_save_round_trip(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    [record] = inbox.ingest_signals("hackernews", "q", [_signal("https://news.ycombinator.com/item?id=9")])
    loaded = inbox.get(record.id)
    assert loaded.id == record.id
