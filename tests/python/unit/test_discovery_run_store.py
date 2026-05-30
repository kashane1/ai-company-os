"""Tests for the DB-backed discovery run store + the migration seam (E3).

Each test gets an isolated repo root so the control-plane SQLite file lives in
tmp, never the real state/ tree. No network — run reports are plain dataclasses.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.discovery_run_store import DiscoveryRunRecordStore
from packages.discovery.run import (
    DiscoveryRunReport,
    DiscoveryRunRepository,
    DiscoveryRunStatus,
    DiscoveryRunStore,
    migrate_runs,
)


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    return tmp_path


def _report(run_id: str, *, started_at: str, status: str = DiscoveryRunStatus.COMPLETED,
            signals: int = 3) -> DiscoveryRunReport:
    return DiscoveryRunReport(
        run_id=run_id,
        status=status,
        queries=["invoice reminders"],
        sources=["hackernews", "github"],
        signals_ingested=signals,
        opportunities_touched=signals,
        sources_hit={"hackernews": 2, "github": 1},
        started_at=started_at,
        finished_at=started_at,
    )


def test_save_and_get_round_trip(isolated: Path) -> None:
    store = DiscoveryRunRecordStore()
    report = _report("run_a", started_at="2026-05-30T10:00:00+00:00")
    store.save(report)
    assert store.get("run_a") == report


def test_get_missing_raises(isolated: Path) -> None:
    store = DiscoveryRunRecordStore()
    with pytest.raises(FileNotFoundError):
        store.get("nope")


def test_latest_returns_most_recently_started(isolated: Path) -> None:
    store = DiscoveryRunRecordStore()
    assert store.latest() is None
    store.save(_report("older", started_at="2026-05-30T09:00:00+00:00"))
    store.save(_report("newer", started_at="2026-05-30T11:00:00+00:00"))
    assert store.latest().run_id == "newer"


def test_save_upserts_on_same_run_id(isolated: Path) -> None:
    # The on_progress snapshots reuse one run_id; an upsert must keep one row.
    store = DiscoveryRunRecordStore()
    store.save(_report("run_x", started_at="2026-05-30T10:00:00+00:00",
                       status=DiscoveryRunStatus.RUNNING, signals=1))
    store.save(_report("run_x", started_at="2026-05-30T10:00:00+00:00",
                       status=DiscoveryRunStatus.COMPLETED, signals=5))
    runs = store.list()
    assert len(runs) == 1
    assert runs[0].status == DiscoveryRunStatus.COMPLETED
    assert runs[0].signals_ingested == 5


def test_list_orders_newest_first(isolated: Path) -> None:
    store = DiscoveryRunRecordStore()
    store.save(_report("a", started_at="2026-05-30T08:00:00+00:00"))
    store.save(_report("b", started_at="2026-05-30T12:00:00+00:00"))
    store.save(_report("c", started_at="2026-05-30T10:00:00+00:00"))
    assert [r.run_id for r in store.list()] == ["b", "c", "a"]


def test_protocol_isinstance_checks(isolated: Path) -> None:
    assert isinstance(DiscoveryRunRecordStore(), DiscoveryRunRepository)
    assert isinstance(DiscoveryRunStore(root=isolated / "runs"), DiscoveryRunRepository)


def test_migrate_file_to_db(isolated: Path) -> None:
    file_store = DiscoveryRunStore(root=isolated / "runs")
    file_store.save(_report("r1", started_at="2026-05-30T09:00:00+00:00"))
    file_store.save(_report("r2", started_at="2026-05-30T10:00:00+00:00"))

    db_store = DiscoveryRunRecordStore()
    copied = migrate_runs(file_store, db_store)

    assert copied == 2
    assert {r.run_id for r in db_store.list()} == {"r1", "r2"}
    assert db_store.latest().run_id == "r2"


def test_file_store_list_skips_current_pointer(isolated: Path) -> None:
    store = DiscoveryRunStore(root=isolated / "runs")
    store.save(_report("r1", started_at="2026-05-30T09:00:00+00:00"))
    # save() writes both r1.json and the current.json pointer; list() must not
    # double-count the pointer.
    assert [r.run_id for r in store.list()] == ["r1"]
