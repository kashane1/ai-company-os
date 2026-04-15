"""Per-skill-id lock store for the Phase 3 skill-evolution worker.

Backed by :class:`packages.db.control_plane_db.ControlPlaneDatabase` so
the same backend choice (SQLite today, Postgres via ``DATABASE_URL``
tomorrow) governs locks and the rest of the control plane. See
``packages/db/locks/__init__.py`` for the design contract.

Schema
------

``INTEGER`` epoch-microseconds for every timestamp so SQLite's numeric
ordering works correctly — see the ``__init__`` docstring for the
rationale against ISO-8601 TEXT columns.

Acquire (single-statement atomic UPSERT)
----------------------------------------

The ``acquire`` path is a single ``INSERT ... ON CONFLICT DO UPDATE``
with a ``WHERE`` clause on the old row's ``heartbeat_at_us``. The
statement is atomic on its own in SQLite — no ``BEGIN IMMEDIATE``
wrapper is required. The caller checks the ``RETURNING holder_token``
value against the token it minted; if the row was held by a live
worker, the conflict path's ``WHERE`` short-circuits to no-op and
``RETURNING`` yields zero rows (or the existing holder's token, which
will not equal the caller's).

Release (single conditional DELETE)
-----------------------------------

The ``release`` path is a single conditional ``DELETE ... RETURNING``.
SQLite wraps single DELETE statements in an implicit transaction and
evaluates the ``WHERE`` during the write — a ``BEGIN IMMEDIATE`` would
add a useless round-trip and extend lock hold time. If the ``RETURNING``
row set is empty, the lock was stolen (the caller's heartbeat fell past
the stale threshold) and the caller MUST abandon its worktree rather
than push any changes.

Heartbeat
---------

Holders extend ``heartbeat_at_us`` every ``HEARTBEAT_INTERVAL_US`` and
the stale threshold is ``HEARTBEAT_INTERVAL_US * 3`` (three missed
heartbeats = stale). Default heartbeat cadence is 60 s, stale threshold
180 s.

Concurrency notes
-----------------

All APIs take ``now_us: int | None`` so tests can freeze time deterministically.
The module binds the backend-agnostic placeholder dialect from
``ControlPlaneDatabase.placeholder`` so the same SQL strings work on
SQLite and Postgres.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any

from packages.db.control_plane_db import ControlPlaneDatabase


SKILL_EVOLUTION_LOCKS_TABLE = "skill_evolution_locks"

# 60 s cadence; holder extends every interval. Three missed heartbeats
# → stale. The worker's main loop must call ``heartbeat()`` well inside
# this window (30 s is a reasonable default for the worker).
HEARTBEAT_INTERVAL_US = 60 * 1_000_000
STALE_THRESHOLD_US = HEARTBEAT_INTERVAL_US * 3


@dataclass(frozen=True)
class SkillEvolutionLock:
    """Public result of an acquire call.

    ``token`` is the handle the caller MUST pass back to ``release`` and
    ``heartbeat``. Do not derive it from the worker id — the point of
    the indirection is that ``release(worker_id, token)`` is keyed to
    this specific acquire, so a stolen-and-reacquired lock cannot be
    accidentally released by the original holder on teardown.
    """

    skill_id: str
    worker_id: str
    token: str
    acquired_at_us: int
    expires_at_us: int


def _now_us() -> int:
    """Epoch microseconds. Wall-clock, not monotonic — the lock store is
    shared-state and must agree across process restarts. Multi-host
    clock skew is out of scope for this platform."""
    return int(time.time() * 1_000_000)


def _mint_token() -> str:
    """uuid4-equivalent 128-bit hex token. ``secrets.token_hex(16)`` is
    stdlib-only and matches the rest of the platform's token shape."""
    return secrets.token_hex(16)


def ensure_schema(db: ControlPlaneDatabase) -> None:
    """Create the lock table and its expiry index if not present.

    Callers typically don't invoke this directly — :func:`acquire` and
    :func:`release` call it on first use. Exposed so tests can prime an
    empty database without going through the full acquire path.
    """
    with db.connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SKILL_EVOLUTION_LOCKS_TABLE} (
                skill_id         TEXT    PRIMARY KEY,
                holder_worker_id TEXT    NOT NULL,
                holder_token     TEXT    NOT NULL,
                acquired_at_us   INTEGER NOT NULL,
                expires_at_us    INTEGER NOT NULL,
                heartbeat_at_us  INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_skill_evo_locks_expires
              ON {SKILL_EVOLUTION_LOCKS_TABLE}(expires_at_us)
            """
        )


class SkillEvolutionLockStore:
    """Backend-agnostic per-skill-id lock store.

    Construct with no arguments in production; pass a test
    :class:`ControlPlaneDatabase` in unit tests to target a temp DB.
    """

    def __init__(self, db: ControlPlaneDatabase | None = None) -> None:
        self._db = db or ControlPlaneDatabase()
        ensure_schema(self._db)

    # ------------------------------------------------------------------ #
    # Acquire                                                             #
    # ------------------------------------------------------------------ #

    def acquire(
        self,
        *,
        skill_id: str,
        worker_id: str,
        ttl_us: int = HEARTBEAT_INTERVAL_US * 10,
        now_us: int | None = None,
    ) -> SkillEvolutionLock | None:
        """Attempt to acquire the lock on ``skill_id`` for ``worker_id``.

        Returns a :class:`SkillEvolutionLock` on success (the caller
        now owns the lock). Returns ``None`` if the lock is held by a
        live worker and has not gone stale. The caller MUST NOT
        re-interpret ``None`` as a retry signal — the worker should
        re-queue the task and move on, not spin.

        The ``ttl_us`` parameter is the advisory expiry (soft cap on
        task duration). The heartbeat system is the real enforcement —
        a worker that exceeds its advisory TTL but is still heartbeating
        keeps the lock.
        """
        current = now_us if now_us is not None else _now_us()
        token = _mint_token()
        stale_cutoff = current - STALE_THRESHOLD_US

        params: dict[str, Any] = {
            "skill_id": skill_id,
            "worker_id": worker_id,
            "token": token,
            "now_us": current,
            "expires_us": current + ttl_us,
            "stale_threshold_us": stale_cutoff,
        }

        query = f"""
            INSERT INTO {SKILL_EVOLUTION_LOCKS_TABLE}
                (skill_id, holder_worker_id, holder_token,
                 acquired_at_us, expires_at_us, heartbeat_at_us)
            VALUES
                ({self._db.placeholder("skill_id")},
                 {self._db.placeholder("worker_id")},
                 {self._db.placeholder("token")},
                 {self._db.placeholder("now_us")},
                 {self._db.placeholder("expires_us")},
                 {self._db.placeholder("now_us")})
            ON CONFLICT(skill_id) DO UPDATE SET
                holder_worker_id = excluded.holder_worker_id,
                holder_token     = excluded.holder_token,
                acquired_at_us   = excluded.acquired_at_us,
                expires_at_us    = excluded.expires_at_us,
                heartbeat_at_us  = excluded.heartbeat_at_us
            WHERE {SKILL_EVOLUTION_LOCKS_TABLE}.heartbeat_at_us
                  < {self._db.placeholder("stale_threshold_us")}
            RETURNING holder_token
        """

        with self._db.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()

        # Three outcomes from the UPSERT:
        #
        # 1. Fresh INSERT (no conflict) — RETURNING yields our token.
        # 2. Conflict, WHERE matches (previous holder went stale) — the
        #    UPDATE overwrites with our token. RETURNING yields our token.
        # 3. Conflict, WHERE false (previous holder still live) — the
        #    UPDATE is a no-op and SQLite's RETURNING yields no rows on
        #    the no-op branch in modern versions. Do NOT trust
        #    ``cursor.rowcount`` here — its behavior for "conflict +
        #    WHERE false → no-op" is inconsistent across SQLite versions.
        if row is None:
            return None
        returned = _row_column(row, "holder_token")
        if returned != token:
            return None

        return SkillEvolutionLock(
            skill_id=skill_id,
            worker_id=worker_id,
            token=token,
            acquired_at_us=current,
            expires_at_us=current + ttl_us,
        )

    # ------------------------------------------------------------------ #
    # Heartbeat                                                           #
    # ------------------------------------------------------------------ #

    def heartbeat(
        self,
        *,
        skill_id: str,
        token: str,
        now_us: int | None = None,
    ) -> bool:
        """Extend the lock by writing a fresh ``heartbeat_at_us``.

        Returns ``True`` on success, ``False`` if the caller no longer
        owns the lock (token mismatch, typically because the stale
        threshold fired and someone else re-acquired). Callers that get
        ``False`` MUST abandon their worktree immediately — another
        worker is now free to race on the same skill.
        """
        current = now_us if now_us is not None else _now_us()
        params = {
            "skill_id": skill_id,
            "token": token,
            "now_us": current,
        }
        query = f"""
            UPDATE {SKILL_EVOLUTION_LOCKS_TABLE}
               SET heartbeat_at_us = {self._db.placeholder("now_us")}
             WHERE skill_id = {self._db.placeholder("skill_id")}
               AND holder_token = {self._db.placeholder("token")}
            RETURNING holder_token
        """
        with self._db.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
        if row is None:
            return False
        returned = _row_column(row, "holder_token")
        return returned == token

    # ------------------------------------------------------------------ #
    # Release                                                             #
    # ------------------------------------------------------------------ #

    def release(
        self,
        *,
        skill_id: str,
        token: str,
    ) -> bool:
        """Release the lock. Returns ``True`` iff the caller's token
        matched and the row was deleted.

        A ``False`` return means the caller's lock was already stolen
        (stale threshold fired, another worker re-acquired). The caller
        MUST treat any work staged during the race window as tainted
        and discard it.
        """
        params = {"skill_id": skill_id, "token": token}
        query = f"""
            DELETE FROM {SKILL_EVOLUTION_LOCKS_TABLE}
             WHERE skill_id = {self._db.placeholder("skill_id")}
               AND holder_token = {self._db.placeholder("token")}
            RETURNING skill_id
        """
        with self._db.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
        return row is not None

    # ------------------------------------------------------------------ #
    # Introspection                                                       #
    # ------------------------------------------------------------------ #

    def is_locked(
        self,
        *,
        skill_id: str,
        now_us: int | None = None,
    ) -> bool:
        """Non-mutating check — is this skill currently locked by a
        live holder?

        Used by :mod:`packages.policies.skill_evolution` to raise
        ``CONCURRENT_EVOLUTION_IN_PROGRESS`` without taking the lock
        itself. A stale lock (heartbeat past threshold) is NOT
        considered locked — it would be stolen on the next acquire.
        """
        current = now_us if now_us is not None else _now_us()
        stale_cutoff = current - STALE_THRESHOLD_US
        query = f"""
            SELECT holder_worker_id
              FROM {SKILL_EVOLUTION_LOCKS_TABLE}
             WHERE skill_id = {self._db.placeholder("skill_id")}
               AND heartbeat_at_us >= {self._db.placeholder("stale_threshold_us")}
        """
        row = self._db.fetch_one(
            query,
            {"skill_id": skill_id, "stale_threshold_us": stale_cutoff},
        )
        return row is not None


def _row_column(row: Any, column: str) -> Any:
    """Extract a named column from a row object that might be either a
    ``sqlite3.Row`` (indexable + mappable) or a ``psycopg`` dict row.
    """
    try:
        return row[column]
    except (KeyError, IndexError, TypeError):
        pass
    if isinstance(row, dict):
        return row.get(column)
    # Fallback: positional at index 0 for single-column RETURNING.
    try:
        return row[0]
    except (IndexError, TypeError):
        return None
