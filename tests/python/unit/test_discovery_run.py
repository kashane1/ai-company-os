"""Tests for the on-demand discovery run controller.

Stub connectors + an injectable stop signal make the whole thing deterministic
and offline — no timers, no real sources.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.discovery.connectors.base import (
    CompliancePolicyError,
    ConnectorConfig,
    FetchOptions,
    RawSignal,
)
from packages.discovery.inbox import OpportunityInbox
from packages.discovery.run import (
    DiscoveryRunReport,
    DiscoveryRunStatus,
    DiscoveryRunStore,
    FileStopSignal,
    run_discovery,
)
from packages.schemas.opportunity import EvidenceKind

FIXED = datetime(2026, 5, 29, tzinfo=timezone.utc)


class StubConnector:
    def __init__(self, cid: str, signals: list[RawSignal], *, raises: bool = False) -> None:
        self.id = cid
        self.config = ConnectorConfig(id=cid)
        self._signals = signals
        self._raises = raises

    def fetch(self, options: FetchOptions) -> list[RawSignal]:
        if self._raises:
            raise CompliancePolicyError("boom")
        return self._signals

    def healthcheck(self) -> tuple[bool, str]:
        return (True, "")


def _inbox(tmp_path: Path) -> OpportunityInbox:
    return OpportunityInbox(root=tmp_path / "opportunities", now=lambda: FIXED)


def _sig(url: str, text: str) -> RawSignal:
    return RawSignal(text=text, url=url, kind=EvidenceKind.REQUEST, quote=text)


def test_run_completes_and_counts_sources(tmp_path: Path) -> None:
    connectors = {
        "hackernews": StubConnector(
            "hackernews", [_sig("https://hn/1", "tool A"), _sig("https://hn/2", "tool B")]
        ),
        "github": StubConnector("github", [_sig("https://gh/1", "tool C")]),
    }
    report = run_discovery(
        inbox=_inbox(tmp_path), connectors=connectors, queries=["q"], now=lambda: FIXED
    )
    assert report.status == DiscoveryRunStatus.COMPLETED
    assert report.signals_ingested == 3
    assert report.sources_hit == {"hackernews": 2, "github": 1}
    assert report.stopped_early is False


def test_run_stops_early_on_signal(tmp_path: Path) -> None:
    connectors = {
        "hackernews": StubConnector("hackernews", [_sig("https://hn/1", "tool A")]),
        "github": StubConnector("github", [_sig("https://gh/1", "tool C")]),
    }
    calls = {"n": 0}

    def should_stop() -> bool:
        calls["n"] += 1
        return calls["n"] > 1  # allow the first unit, stop before the second

    report = run_discovery(
        inbox=_inbox(tmp_path), connectors=connectors, queries=["q"],
        should_stop=should_stop, now=lambda: FIXED,
    )
    assert report.status == DiscoveryRunStatus.STOPPED
    assert report.stopped_early is True
    assert report.signals_ingested == 1  # only the first source ran


def test_run_records_connector_errors_and_continues(tmp_path: Path) -> None:
    connectors = {
        "broken": StubConnector("broken", [], raises=True),
        "github": StubConnector("github", [_sig("https://gh/1", "tool C")]),
    }
    report = run_discovery(
        inbox=_inbox(tmp_path), connectors=connectors, queries=["q"], now=lambda: FIXED
    )
    assert report.status == DiscoveryRunStatus.COMPLETED
    assert any("broken" in e for e in report.errors)
    assert report.signals_ingested == 1  # the healthy source still ran


def test_report_round_trip() -> None:
    report = DiscoveryRunReport(
        run_id="run_1", status="completed", queries=["q"], sources=["hackernews"],
        signals_ingested=2, sources_hit={"hackernews": 2}, started_at="t0", finished_at="t1",
    )
    assert DiscoveryRunReport.from_dict(report.to_dict()) == report


def test_run_store_saves_and_reads_latest(tmp_path: Path) -> None:
    store = DiscoveryRunStore(root=tmp_path / "runs")
    assert store.latest() is None
    report = DiscoveryRunReport(run_id="run_1", status="completed")
    store.save(report)
    assert store.latest().run_id == "run_1"


def test_file_stop_signal(tmp_path: Path) -> None:
    stop = FileStopSignal(root=tmp_path / "runs")
    assert stop.requested() is False
    stop.request()
    assert stop() is True  # callable form
    stop.clear()
    assert stop.requested() is False
