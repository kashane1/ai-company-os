"""Tests for the discovery dashboard view builder + HTML renderer (D3).

Pure and offline: the view is built from in-memory/file repositories, so these
exercise the ranking, the run-history wiring, and the HTML escaping without a
web server or DB. The FastAPI router on top is a thin adapter.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.discovery.dashboard import build_dashboard, render_html
from packages.discovery.run import DiscoveryRunReport, DiscoveryRunStatus, DiscoveryRunStore
from packages.schemas.opportunity import (
    EvidenceKind,
    EvidenceLink,
    OpportunityRecord,
    OpportunityStatus,
    SourceRef,
)

FIXED = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)


class _MemOpportunities:
    def __init__(self, records: list[OpportunityRecord]) -> None:
        self._records = records

    def list(self) -> list[OpportunityRecord]:
        return list(self._records)


def _opp(opp_id: str, *, score: float | None, status: OpportunityStatus,
         title: str = "wedge", connector: str = "hackernews") -> OpportunityRecord:
    return OpportunityRecord(
        id=opp_id,
        title=title,
        problem="p",
        audience="freelancers",
        source=SourceRef(connector=connector, query="q"),
        status=status,
        evidence=[EvidenceLink(url="https://news.ycombinator.com/item?id=1",
                               kind=EvidenceKind.REQUEST)],
        score=score,
        confidence=0.8 if score is not None else None,
        created_at="2026-05-29T00:00:00+00:00",
        updated_at="2026-05-29T00:00:00+00:00",
    )


def _run(run_id: str, started_at: str, signals: int = 3) -> DiscoveryRunReport:
    return DiscoveryRunReport(
        run_id=run_id,
        status=DiscoveryRunStatus.COMPLETED,
        queries=["invoice reminders"],
        sources=["hackernews"],
        signals_ingested=signals,
        sources_hit={"hackernews": signals},
        started_at=started_at,
        finished_at=started_at,
    )


def test_inbox_ranked_scored_first_then_by_score(tmp_path: Path) -> None:
    opps = _MemOpportunities([
        _opp("a", score=None, status=OpportunityStatus.INBOX, title="unscored"),
        _opp("b", score=72.0, status=OpportunityStatus.SCORED, title="high"),
        _opp("c", score=40.0, status=OpportunityStatus.SCORED, title="low"),
    ])
    runs = DiscoveryRunStore(root=tmp_path / "runs")
    view = build_dashboard(opps, runs, now=lambda: FIXED)

    assert view.total_opportunities == 3
    assert [row.title for row in view.inbox] == ["high", "low", "unscored"]
    assert view.status_counts == {"inbox": 1, "scored": 2}
    assert view.latest_run is None


def test_run_status_and_history_included(tmp_path: Path) -> None:
    runs = DiscoveryRunStore(root=tmp_path / "runs")
    runs.save(_run("older", "2026-05-30T09:00:00+00:00"))
    runs.save(_run("newer", "2026-05-30T11:00:00+00:00", signals=5))

    view = build_dashboard(_MemOpportunities([]), runs, now=lambda: FIXED)

    assert view.latest_run is not None
    assert view.latest_run.run_id == "newer"
    assert view.latest_run.signals_ingested == 5
    assert [r.run_id for r in view.recent_runs] == ["newer", "older"]


def test_inbox_limit_caps_rows(tmp_path: Path) -> None:
    opps = _MemOpportunities([
        _opp(f"id{i}", score=float(i), status=OpportunityStatus.SCORED) for i in range(30)
    ])
    runs = DiscoveryRunStore(root=tmp_path / "runs")
    view = build_dashboard(opps, runs, inbox_limit=5, now=lambda: FIXED)
    assert len(view.inbox) == 5
    assert view.total_opportunities == 30  # count reflects all, not just shown


def test_render_html_contains_data_and_escapes(tmp_path: Path) -> None:
    opps = _MemOpportunities([
        _opp("x", score=88.0, status=OpportunityStatus.SCORED, title="Tag <b>injection</b>"),
    ])
    runs = DiscoveryRunStore(root=tmp_path / "runs")
    runs.save(_run("run_1", "2026-05-30T11:00:00+00:00"))
    view = build_dashboard(opps, runs, now=lambda: FIXED)

    out = render_html(view)
    assert "<!doctype html>" in out
    assert "Discovery" in out
    assert "run_1" in out
    assert "88" in out
    # The malicious title must be escaped, not rendered as a tag.
    assert "Tag &lt;b&gt;injection&lt;/b&gt;" in out
    assert "<b>injection</b>" not in out


def test_empty_state_renders(tmp_path: Path) -> None:
    runs = DiscoveryRunStore(root=tmp_path / "runs")
    view = build_dashboard(_MemOpportunities([]), runs, now=lambda: FIXED)
    out = render_html(view)
    assert "No discovery runs recorded yet." in out
    assert "Inbox is empty" in out


def test_view_to_dict_is_json_shaped(tmp_path: Path) -> None:
    opps = _MemOpportunities([_opp("x", score=50.0, status=OpportunityStatus.SCORED)])
    runs = DiscoveryRunStore(root=tmp_path / "runs")
    runs.save(_run("run_1", "2026-05-30T11:00:00+00:00"))
    payload = build_dashboard(opps, runs, now=lambda: FIXED).to_dict()

    assert payload["total_opportunities"] == 1
    assert payload["latest_run"]["run_id"] == "run_1"
    assert payload["inbox"][0]["score"] == 50.0
    import json

    json.dumps(payload)  # must be serializable
