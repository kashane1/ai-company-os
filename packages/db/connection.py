"""Canonical SQLite connection bootstrap for the platform.

Every caller in packages/db/ and packages/queue/ that opens a SQLite
connection routes through `open_platform_db` so WAL / busy_timeout /
synchronous settings are guaranteed consistent across the platform.

Before this module existed, `packages/db/control_plane_db.py` called
`sqlite3.connect(db_path)` directly — which means every new connection
started with `busy_timeout=0` (immediate SQLITE_BUSY on any contention)
and whatever journal mode was stored in the file header, typically
DELETE. Under Phase 3's concurrent skill-evolution workers combined
with Phase 1's autonomous dispatch, that produced writer starvation
invisible at 20 tasks/week and catastrophic under real load.

This helper fixes it once, for every caller, without changing caller
APIs.

Design notes carried forward from the deepening + technical review:

- **isolation_level is NOT forced.** An earlier draft set
  `isolation_level=None` (autocommit mode), which silently breaks every
  `with conn:` context-manager transaction in existing stores. The
  current shape leaves `isolation_level` at its default so callers
  keep working. The `skill_evolution_locks` store (Phase 3) issues its
  own `BEGIN IMMEDIATE` where needed.

- **check_same_thread=False** lets the background dispatch-health
  flush thread and launchd cron scripts share a connection with the
  main thread. BUT sqlite3's statement cache and per-connection
  transaction state are NOT thread-safe even with this flag. Callers
  MUST either (a) hold an external threading.Lock around every
  `with conn:` block that issues multiple statements, or (b) use
  one connection per thread. Do NOT share a single connection across
  threads without a lock.

- **AI_COMPANY_OS_DISABLE_WAL=1** is the hotfix escape hatch (D7
  hardening rule). If a concurrent-writers regression lands on main
  after Phase 0.5b ships, set the env var, nuke `state/db/*.db-wal`,
  and restart. New connections revert to DELETE-mode journal; file
  headers that already have WAL persist until you manually downgrade.
  See docs/runbooks/sqlite-wal-hotfix.md.

Part of docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md
X2 + Phase 0.5b.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

DISABLE_WAL_ENV_VAR = "AI_COMPANY_OS_DISABLE_WAL"

# Per-path cache of DB files whose WAL mode has already been activated
# by this process. WAL is a file-level property stored in the SQLite
# header, so a single `PRAGMA journal_mode=WAL` per file is enough —
# subsequent connections pick up WAL automatically from the header.
#
# Without this cache, `ControlPlaneDatabase.connection()` (which opens
# a fresh connection on every execute() call via its @contextmanager
# decorator) runs the WAL pragma on every open, and in the single-
# threaded benchmark the pragma overhead dominates latency. Caching
# here drops that cost to a single initialization per process lifetime
# per DB file.
_wal_initialized: set[str] = set()
_wal_lock = threading.Lock()


def open_platform_db(
    path: Path | str,
    *,
    read_only: bool = False,
) -> sqlite3.Connection:
    """Open a SQLite connection with platform-standard settings.

    Args:
        path: Filesystem path to the SQLite database file. Parent
            directory is created automatically if it doesn't exist.
        read_only: If True, opens the DB via URI in read-only mode.
            Read-only connections still see committed writes from
            other processes (WAL coherency).

    Returns:
        An `sqlite3.Connection` with WAL, busy_timeout=30000,
        synchronous=NORMAL, foreign_keys=ON, temp_store=MEMORY,
        and mmap_size=256 MiB applied.

    Thread safety:
        The returned connection has `check_same_thread=False`. See
        module docstring for the locking contract callers must follow.
    """
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if read_only:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(
            uri,
            timeout=30.0,
            check_same_thread=False,
            uri=True,
        )
        # Read-only connections still benefit from busy_timeout for shared
        # locks, but don't set journal_mode (the file's existing mode is
        # used). Apply the rest of the read-path pragmas.
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256 MiB
        return conn

    conn = sqlite3.connect(
        db_path,
        timeout=30.0,
        check_same_thread=False,
    )
    # DO NOT set isolation_level=None — see module docstring. Callers
    # that need explicit write locks issue `BEGIN IMMEDIATE` themselves.

    # busy_timeout is per-connection and MUST be set before any write
    # contention, or we race with the default 0ms timeout on first
    # write. D2 commit-ordering rule.
    conn.execute("PRAGMA busy_timeout=30000")

    # WAL is per-file (stored in header). Only activate it once per
    # path per process; subsequent connections pick up WAL from the
    # header for free. This is the biggest single-connection perf
    # optimization in the helper.
    #
    # D7 hotfix escape hatch: AI_COMPANY_OS_DISABLE_WAL=1 skips the
    # activation entirely. Existing WAL-mode DB files still operate in
    # WAL until manually downgraded.
    if os.environ.get(DISABLE_WAL_ENV_VAR) != "1":
        cache_key = str(db_path.resolve())
        if cache_key not in _wal_initialized:
            with _wal_lock:
                if cache_key not in _wal_initialized:
                    conn.execute("PRAGMA journal_mode=WAL")
                    _wal_initialized.add(cache_key)

    # synchronous and foreign_keys are per-connection. Keep them — both
    # are cheap flag flips, and foreign_keys=ON is required for any
    # future schema with FK relationships.
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


def _reset_wal_cache_for_tests() -> None:
    """Test-only helper: clear the per-process WAL initialization cache.

    Used by `test_concurrent_writers.py` and similar tests that need
    to exercise the first-open-per-path path repeatedly. Never call
    from production code.
    """
    with _wal_lock:
        _wal_initialized.clear()
