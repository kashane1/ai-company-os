"""Phase 3 — unit tests for packages/db/locks/skill_evolution.py."""
from __future__ import annotations

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.control_plane_db import ControlPlaneDatabase
from packages.db.locks.skill_evolution import (
    HEARTBEAT_INTERVAL_US,
    STALE_THRESHOLD_US,
    SkillEvolutionLockStore,
)


@pytest.fixture
def store(tmp_path, monkeypatch) -> SkillEvolutionLockStore:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    return SkillEvolutionLockStore(ControlPlaneDatabase())


def test_acquire_on_empty_table_returns_lock(store: SkillEvolutionLockStore) -> None:
    lock = store.acquire(
        skill_id="demo-skill",
        worker_id="worker-a",
        now_us=1_000_000,
    )
    assert lock is not None
    assert lock.skill_id == "demo-skill"
    assert lock.worker_id == "worker-a"
    # Token is 128-bit hex (uuid4-equivalent via secrets.token_hex(16)).
    assert len(lock.token) == 32


def test_acquire_blocks_concurrent_fresh_holder(store: SkillEvolutionLockStore) -> None:
    first = store.acquire(skill_id="demo-skill", worker_id="a", now_us=1_000_000)
    assert first is not None

    # Second acquire inside the stale window must return None.
    second = store.acquire(
        skill_id="demo-skill",
        worker_id="b",
        now_us=1_000_000 + 30 * 1_000_000,  # 30 s later, well under stale
    )
    assert second is None


def test_acquire_steals_stale_holder(store: SkillEvolutionLockStore) -> None:
    first = store.acquire(skill_id="demo-skill", worker_id="a", now_us=1_000_000)
    assert first is not None

    # Jump past the stale threshold.
    far_future = 1_000_000 + STALE_THRESHOLD_US + 1
    second = store.acquire(
        skill_id="demo-skill", worker_id="b", now_us=far_future
    )
    assert second is not None
    assert second.worker_id == "b"


def test_heartbeat_keeps_lock_alive(store: SkillEvolutionLockStore) -> None:
    lock = store.acquire(skill_id="demo", worker_id="a", now_us=0)
    assert lock is not None

    # Extend at 60s.
    assert store.heartbeat(
        skill_id="demo", token=lock.token, now_us=60 * 1_000_000
    )

    # Another worker tries to acquire at 120s — inside stale window,
    # heartbeat was recent → denied.
    second = store.acquire(
        skill_id="demo", worker_id="b", now_us=120 * 1_000_000
    )
    assert second is None


def test_heartbeat_with_wrong_token_returns_false(store: SkillEvolutionLockStore) -> None:
    lock = store.acquire(skill_id="demo", worker_id="a", now_us=0)
    assert lock is not None
    assert not store.heartbeat(skill_id="demo", token="bogus", now_us=1_000)


def test_release_with_correct_token_deletes_row(store: SkillEvolutionLockStore) -> None:
    lock = store.acquire(skill_id="demo", worker_id="a", now_us=0)
    assert lock is not None
    assert store.release(skill_id="demo", token=lock.token)
    # Fresh acquire now succeeds immediately.
    again = store.acquire(skill_id="demo", worker_id="b", now_us=1)
    assert again is not None


def test_release_with_wrong_token_is_noop(store: SkillEvolutionLockStore) -> None:
    lock = store.acquire(skill_id="demo", worker_id="a", now_us=0)
    assert lock is not None
    assert not store.release(skill_id="demo", token="nope")
    # Original lock still held.
    again = store.acquire(skill_id="demo", worker_id="b", now_us=100)
    assert again is None


def test_is_locked_reflects_live_holder(store: SkillEvolutionLockStore) -> None:
    assert not store.is_locked(skill_id="demo", now_us=0)
    lock = store.acquire(skill_id="demo", worker_id="a", now_us=0)
    assert lock is not None
    assert store.is_locked(skill_id="demo", now_us=1_000)
    # Past the stale window, is_locked returns False even though the
    # row is still present — the row will be stolen on next acquire.
    assert not store.is_locked(
        skill_id="demo", now_us=STALE_THRESHOLD_US + 1
    )


def test_stale_threshold_is_three_heartbeat_intervals() -> None:
    # Structural assertion — any change to the cadence pair is a
    # breaking protocol change and should show up in a diff review.
    assert STALE_THRESHOLD_US == HEARTBEAT_INTERVAL_US * 3
    assert HEARTBEAT_INTERVAL_US == 60 * 1_000_000
