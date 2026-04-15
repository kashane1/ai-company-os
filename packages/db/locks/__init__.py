"""Per-subject lock stores backed by ``ControlPlaneDatabase``.

Phase 3 introduces the first member (``skill_evolution``) for per-skill-id
mutual exclusion on proposal generation. Phase 4 plans to add per-peer
locks for ACP handshake state transitions, reusing the same pattern.

Every lock store in this package MUST:

1. Use :class:`packages.db.control_plane_db.ControlPlaneDatabase` as its
   backend — never a sidecar SQLite file. The operator flipping
   ``AI_COMPANY_OS_DATABASE_URL`` to Postgres must move locks with it.
2. Store timestamps as ``INTEGER`` epoch-microseconds, NOT ISO-8601 TEXT.
   Numeric compare is DST-immune, tz-immune, and immune to ISO-8601
   length drift (``2026-04-14T10:00:00Z`` vs
   ``2026-04-14T10:00:00.123456+00:00`` misorder lexicographically).
3. Use a ``holder_token`` (uuid4 hex) alongside ``holder_worker_id`` so
   release is keyed to the specific acquire, not just the worker
   identity. Protects against "stolen lock, original worker still
   running" races.
4. Extend the lock via a heartbeat column, NOT rely on a pure TTL. A
   worker hanging past its TTL while still holding the worktree will
   have its lock stolen under a pure-TTL scheme; heartbeat + holder
   token is the fix.
"""
