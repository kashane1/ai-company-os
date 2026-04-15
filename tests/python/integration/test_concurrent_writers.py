"""Phase 0.5b — concurrent writer contention test for the SQLite bootstrap.

Spawns N=8 concurrent writer threads against a single temp DB and
asserts zero SQLITE_BUSY errors plus p99 < 20 ms. Without WAL and
busy_timeout=30000 (applied by `packages/db/connection.py`), this
test would fail immediately with the default busy_timeout=0.

Also includes the D2 hardening guard: verifies that opening a fresh
DB via `open_platform_db` applies WAL and busy_timeout in the right
order (busy_timeout non-zero before any concurrent write can hit it).
"""
from __future__ import annotations

import sqlite3
import statistics
import threading
import time
from pathlib import Path

import pytest

from packages.db.connection import (
    _reset_wal_cache_for_tests,
    open_platform_db,
)


N_WRITERS = 8
CYCLES_PER_WRITER = 100


@pytest.fixture(autouse=True)
def _reset_wal_cache():
    """Each test starts with a clean per-path WAL init cache."""
    _reset_wal_cache_for_tests()
    yield
    _reset_wal_cache_for_tests()


def test_open_platform_db_sets_wal_and_busy_timeout(tmp_path: Path) -> None:
    """Smoke test — every new connection gets WAL + 30s busy_timeout."""
    db = tmp_path / "smoke.db"
    conn = open_platform_db(db)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1  # NORMAL
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_context_manager_transactions_still_commit(tmp_path: Path) -> None:
    """Autocommit regression guard (D6 hardening rule).

    An earlier draft of `open_platform_db` passed `isolation_level=None`
    which silently broke `with conn:` context-manager transactions — the
    caller's implicit commit became a no-op and data was lost on exit.

    This test asserts that `with conn: conn.execute("INSERT ...")` still
    commits so existing callers (approval_store, release_store, etc.)
    keep working. Uses an ephemeral bench_writes table — NEVER references
    any schema introduced in Phase 1+ so Phase 0.5b has no forward
    dependency.
    """
    db = tmp_path / "autocommit.db"
    conn = open_platform_db(db)
    try:
        conn.execute(
            "CREATE TABLE bench_writes (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
        )
        # Write through the context manager — this is the shape callers use.
        with conn:
            conn.execute("INSERT INTO bench_writes (value) VALUES (?)", ("hello",))
            conn.execute("INSERT INTO bench_writes (value) VALUES (?)", ("world",))
        # Reopen to prove the writes landed and weren't rolled back on close.
    finally:
        conn.close()

    reopened = open_platform_db(db)
    try:
        rows = reopened.execute(
            "SELECT value FROM bench_writes ORDER BY id"
        ).fetchall()
    finally:
        reopened.close()

    assert [r[0] for r in rows] == ["hello", "world"]


def test_concurrent_writers_no_sqlite_busy(tmp_path: Path) -> None:
    """Phase 0.5b — the core justification for the whole bootstrap.

    N=8 threads, each doing 100 INSERT cycles on a shared DB. Without
    `busy_timeout=30000`, writers serialize on the default 0ms timeout
    and one of them immediately hits `sqlite3.OperationalError: database
    is locked`. With the bootstrap helper applied, every write completes
    and tail latency stays bounded.

    Asserts zero SQLITE_BUSY errors and p99 < 20ms (the plan's budget).
    """
    db = tmp_path / "contention.db"

    # Initialize schema from the main thread first.
    init = open_platform_db(db)
    try:
        init.execute(
            "CREATE TABLE bench_writes (id INTEGER PRIMARY KEY, "
            "worker INTEGER NOT NULL, cycle INTEGER NOT NULL)"
        )
    finally:
        init.close()

    latencies_ms: list[float] = []
    errors: list[str] = []
    lock = threading.Lock()

    def worker(worker_id: int) -> None:
        # One connection per thread (per the connection.py docstring).
        conn = open_platform_db(db)
        try:
            for cycle in range(CYCLES_PER_WRITER):
                start = time.perf_counter()
                try:
                    with conn:
                        conn.execute(
                            "INSERT INTO bench_writes (worker, cycle) VALUES (?, ?)",
                            (worker_id, cycle),
                        )
                except sqlite3.OperationalError as e:
                    with lock:
                        errors.append(f"worker {worker_id} cycle {cycle}: {e}")
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                with lock:
                    latencies_ms.append(elapsed_ms)
        finally:
            conn.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_WRITERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], (
        f"SQLITE_BUSY or similar errors occurred "
        f"({len(errors)}/{N_WRITERS * CYCLES_PER_WRITER} writes): {errors[:5]}"
    )

    # Verify all writes landed.
    verify = open_platform_db(db)
    try:
        count = verify.execute("SELECT COUNT(*) FROM bench_writes").fetchone()[0]
    finally:
        verify.close()
    assert count == N_WRITERS * CYCLES_PER_WRITER, (
        f"expected {N_WRITERS * CYCLES_PER_WRITER} writes, got {count}"
    )

    # Latency budget.
    latencies_ms.sort()
    p99 = latencies_ms[min(int(len(latencies_ms) * 0.99), len(latencies_ms) - 1)]
    median = statistics.median(latencies_ms)
    print(
        f"\nconcurrent writers: {N_WRITERS} x {CYCLES_PER_WRITER} cycles  "
        f"median={median:.3f}ms  p99={p99:.3f}ms"
    )
    assert p99 < 20.0, f"p99 write latency {p99:.2f}ms exceeds 20ms budget"


def test_read_only_connection_opens_cleanly(tmp_path: Path) -> None:
    """Read-only URI connections work and see committed writes."""
    db = tmp_path / "ro.db"

    # Write some data via a normal connection.
    writer = open_platform_db(db)
    try:
        writer.execute("CREATE TABLE snapshot (value TEXT)")
        with writer:
            writer.execute("INSERT INTO snapshot VALUES (?)", ("committed",))
    finally:
        writer.close()

    # Open read-only.
    reader = open_platform_db(db, read_only=True)
    try:
        rows = reader.execute("SELECT value FROM snapshot").fetchall()
        assert [r[0] for r in rows] == ["committed"]
        # Writes from a read-only connection should fail.
        with pytest.raises(sqlite3.OperationalError):
            reader.execute("INSERT INTO snapshot VALUES (?)", ("nope",))
    finally:
        reader.close()


def test_disable_wal_env_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """D7 hotfix escape hatch — AI_COMPANY_OS_DISABLE_WAL=1 skips WAL.

    File-header WAL persists once set by another connection, so this test
    uses a fresh DB to prove the flag prevents WAL activation on new DBs.
    """
    monkeypatch.setenv("AI_COMPANY_OS_DISABLE_WAL", "1")
    db = tmp_path / "no_wal.db"
    conn = open_platform_db(db)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0].lower()
        assert mode != "wal", f"expected non-WAL journal mode, got {mode!r}"
        # busy_timeout must still be set even when WAL is skipped.
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
    finally:
        conn.close()
