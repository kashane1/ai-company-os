"""Agent-callable primitives (Phase 0.5e).

Every module in this subpackage is:

1. Stateless at module level — no mutable global state, no module-
   level work that touches filesystem / network / env.
2. Side-effect-free to import — imports never spawn threads, open
   sockets, read config, or trigger anything other than name binding.
3. Returns typed values — frozen dataclasses, Protocol instances, or
   primitive Python types (str/int/bool/tuple of those).
4. Contains no orchestration — each public function is a single
   operation. Loops and multi-step flows belong in workers.

Convention enforced by `tests/python/unit/test_primitives_conventions.py`.

Phase-owned modules that will land here:

- `dispatch_health_reader.py` — Phase 0.5e (cross-cutting observability).
- `kill_switches.py`          — Phase 3 (agent-readable kill switches).
- `peer_runtimes.py`          — Phase 4 (CRUD on ACP peers).
- `approvals.py`              — Phase 5 (request/submit approval tokens).

See `docs/adr/2026-04-14-primitives-subpackage.md` for the full
convention contract.
"""
