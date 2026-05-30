"""Tests for semantic dedup — uses a deterministic stub embedding provider."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.discovery.connectors.base import RawSignal
from packages.discovery.inbox import OpportunityInbox
from packages.discovery.semantic import (
    SemanticDeduper,
    cosine,
    ingest_with_semantic_dedup,
)
from packages.schemas.opportunity import EvidenceKind


def _stub_embedding(text: str) -> list[float]:
    """Toy embedding: presence of topic keywords. Same topic => same vector."""
    t = text.lower()
    return [
        1.0 if ("resize" in t or "resizing" in t) else 0.0,
        1.0 if "invoice" in t or "invoicing" in t else 0.0,
        1.0,  # constant dim keeps norm non-zero
    ]


def _inbox(tmp_path: Path) -> OpportunityInbox:
    fixed = datetime(2026, 5, 29, tzinfo=timezone.utc)
    return OpportunityInbox(root=tmp_path / "opportunities", now=lambda: fixed)


def _signal(url: str, text: str) -> RawSignal:
    return RawSignal(text=text, url=url, kind=EvidenceKind.REQUEST, quote=text)


def test_cosine_basics() -> None:
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0
    assert cosine([0, 0], [1, 1]) == 0.0  # zero vector -> 0, no div error


def test_different_wording_same_pain_merges(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    ingest_with_semantic_dedup(
        inbox, "hackernews", "resize",
        [_signal("https://news.ycombinator.com/item?id=1", "Auto-resize photos for each store")],
        provider=_stub_embedding,
    )
    ingest_with_semantic_dedup(
        inbox, "github", "resize",
        [_signal("https://github.com/x/y/issues/2", "Batch-resize images per marketplace tool")],
        provider=_stub_embedding,
    )
    records = inbox.list()
    assert len(records) == 1  # folded together despite different titles
    assert len(records[0].evidence) == 2


def test_distinct_pain_creates_new_record(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    ingest_with_semantic_dedup(
        inbox, "hackernews", "q",
        [_signal("https://news.ycombinator.com/item?id=1", "Auto-resize photos for each store")],
        provider=_stub_embedding,
    )
    ingest_with_semantic_dedup(
        inbox, "hackernews", "q",
        [_signal("https://news.ycombinator.com/item?id=2", "Tool to automate invoicing")],
        provider=_stub_embedding,
    )
    assert len(inbox.list()) == 2  # resize vs invoicing are not merged


def test_deduper_returns_none_when_below_threshold(tmp_path: Path) -> None:
    inbox = _inbox(tmp_path)
    inbox.ingest_signals(
        "hackernews", "q",
        [_signal("https://news.ycombinator.com/item?id=1", "Auto-resize photos")],
    )
    deduper = SemanticDeduper(_stub_embedding, threshold=0.95)
    # An invoicing query is well below 0.95 similarity to the resize record.
    assert deduper.find_duplicate("automate invoicing", inbox.list()) is None
