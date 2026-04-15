"""Runtime supervisor — core + worker specs + dispatch router.

Split into three modules per Phase 0.5c of
docs/plans/2026-04-14-feat-hermes-inspired-platform-upgrade-plan.md:

- `core.py`          — RuntimeSupervisor class, poll loop, status types
- `specs.py`         — `default_worker_specs()` + `WorkerProcessSpec`
- `dispatch_router.py` — target_runtime → Provider resolution (~50 LOC budget)

`apps/runtime-supervisor/main.py` is a 2-line launchd shim that calls
`run_main()` from this package.
"""
from __future__ import annotations

from .core import (
    ManagedProcess,
    ManagedWorker,
    RuntimeSupervisor,
    SupervisorStatus,
    WorkerProcessStatus,
    load_supervisor_status,
    request_supervisor_shutdown,
    run_main,
)
from .specs import WorkerProcessSpec, default_worker_specs

__all__ = [
    "ManagedProcess",
    "ManagedWorker",
    "RuntimeSupervisor",
    "SupervisorStatus",
    "WorkerProcessSpec",
    "WorkerProcessStatus",
    "default_worker_specs",
    "load_supervisor_status",
    "request_supervisor_shutdown",
    "run_main",
]
