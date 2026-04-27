"""PostMortemStore tests (Phase 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.db.postmortem_store import PostMortemStore
from packages.schemas.postmortem import (
    PostMortem,
    PostMortemSeverity,
    PostMortemStatus,
    RootCauseCategory,
)


def _make(id: str = "abc1234567", *, status: PostMortemStatus = PostMortemStatus.OPEN, created_at: str = "2026-04-27T10:00:00+00:00") -> PostMortem:
    return PostMortem(
        id=id,
        created_at=created_at,
        updated_at=created_at,
        failure_code="lint_failed",
        lane="engineering",
        status=status,
    )


def _store(tmp_path: Path) -> PostMortemStore:
    return PostMortemStore(
        root=tmp_path / "postmortems",
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )


def test_save_and_load_round_trip(tmp_path: Path):
    store = _store(tmp_path)
    pm = _make()
    store.save(pm)
    loaded = store.load(pm.id)
    assert loaded == pm


def test_load_returns_none_for_missing_id(tmp_path: Path):
    store = _store(tmp_path)
    assert store.load("does-not-exist") is None


def test_list_recent_honors_visibility_window(tmp_path: Path):
    store = _store(tmp_path)
    fresh = _make("fresh11111", created_at="2026-04-20T10:00:00+00:00")
    old = _make("old1111111", created_at="2025-12-01T10:00:00+00:00")
    store.save(fresh)
    store.save(old)
    recent = store.list_recent(now_iso="2026-04-27T10:00:00+00:00", max_age_days=90)
    ids = {r.id for r in recent}
    assert "fresh11111" in ids
    assert "old1111111" not in ids


def test_list_open_stale_only_returns_open_records(tmp_path: Path):
    store = _store(tmp_path)
    stale_open = _make("staleopen1", created_at="2026-04-01T10:00:00+00:00")
    stale_resolved = _make(
        "staleresolved",
        status=PostMortemStatus.RESOLVED,
        created_at="2026-04-01T10:00:00+00:00",
    )
    fresh_open = _make("freshopen1", created_at="2026-04-26T10:00:00+00:00")
    for r in (stale_open, stale_resolved, fresh_open):
        store.save(r)
    stale = store.list_open_stale(now_iso="2026-04-27T10:00:00+00:00", threshold_days=14)
    ids = {r.id for r in stale}
    assert ids == {"staleopen1"}


def test_update_status_writes_audit_record(tmp_path: Path):
    store = _store(tmp_path)
    pm = _make()
    store.save(pm)
    updated = store.update_status(
        pm.id,
        status=PostMortemStatus.RESOLVED,
        now_iso="2026-04-28T10:00:00+00:00",
        caller_identity="founder@local",
        notes="fixed in PR #123",
    )
    assert updated.status is PostMortemStatus.RESOLVED
    assert updated.updated_at == "2026-04-28T10:00:00+00:00"
    audit = store.read_audit_log()
    assert len(audit) == 1
    assert audit[0]["postmortem_id"] == pm.id
    assert audit[0]["new_status"] == "resolved"
    assert audit[0]["prev_status"] == "open"
    assert audit[0]["caller_identity"] == "founder@local"


def test_update_status_raises_on_missing_id(tmp_path: Path):
    store = _store(tmp_path)
    with pytest.raises(KeyError):
        store.update_status(
            "does-not-exist",
            status=PostMortemStatus.RESOLVED,
            now_iso="2026-04-28T10:00:00+00:00",
            caller_identity="x",
        )


def test_corrupt_file_is_skipped_not_raised(tmp_path: Path):
    store = _store(tmp_path)
    pm = _make()
    store.save(pm)
    # Drop a corrupt JSON file alongside.
    (store.root / "corrupt.json").write_text("{not json")
    # list_recent should still return the good record.
    recent = store.list_recent(now_iso="2026-04-27T10:00:00+00:00")
    assert [r.id for r in recent] == [pm.id]


def test_index_json_is_optional_and_ignored(tmp_path: Path):
    """M3 fix: deleting/missing index.json must not affect correctness."""
    store = _store(tmp_path)
    pm = _make()
    store.save(pm)
    # Drop a stale index.json
    (store.root / "index.json").write_text("{}")
    recent = store.list_recent(now_iso="2026-04-27T10:00:00+00:00")
    assert [r.id for r in recent] == [pm.id]


def test_concurrent_distinct_id_writes_do_not_corrupt(tmp_path: Path):
    """Two distinct IDs written close together both persist."""
    import threading

    store = _store(tmp_path)
    errors = []

    def writer(idx: int):
        try:
            store.save(_make(id=f"id{idx:08d}"))
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    files = list(store.root.glob("*.json"))
    assert len(files) == 20
