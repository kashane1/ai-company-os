"""Runtime supervisor launchd entrypoint — shim for the three-file split.

Phase 0.5c retained this file as a 2-line shim so the launchd plist
and any downstream tooling that references `apps/runtime-supervisor/main.py`
keeps working. All real logic lives in the `supervisor/` subpackage
alongside this file.

- `supervisor/core.py`           — RuntimeSupervisor class + poll loop
- `supervisor/specs.py`          — default_worker_specs()
- `supervisor/dispatch_router.py` — target_runtime → Provider (50 LOC budget)

Backward-compat re-exports are provided at the bottom of this module
for any existing callers that imported names directly from main.py
(e.g. `from apps.runtime-supervisor.main import RuntimeSupervisor` is
not valid Python syntax, but importlib-based callers may exist).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Make the sibling `supervisor/` subpackage importable by adding this
# script's directory to sys.path. The hyphen in `runtime-supervisor`
# means we can't use `from apps.runtime-supervisor.supervisor import ...`
# as a normal module import.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from packages.config.settings import ensure_runtime_directories  # noqa: E402
from supervisor import (  # noqa: E402  (intentional post-sys.path-insert)
    ManagedProcess,
    ManagedWorker,
    RuntimeSupervisor,
    SupervisorStatus,
    WorkerProcessSpec,
    WorkerProcessStatus,
    default_worker_specs,
    load_supervisor_status,
    request_supervisor_shutdown,
    run_main,
)

# Backward-compat: re-export names at module level so callers that did
# `importlib.import_module("main")` or similar still find them.
# `ensure_runtime_directories` is re-exported because the pre-split
# main.py imported it at module level and the CLI tests access it via
# `runtime_supervisor_main.ensure_runtime_directories()`.
__all__ = [
    "ManagedProcess",
    "ManagedWorker",
    "RuntimeSupervisor",
    "SupervisorStatus",
    "WorkerProcessSpec",
    "WorkerProcessStatus",
    "default_worker_specs",
    "ensure_runtime_directories",
    "load_supervisor_status",
    "request_supervisor_shutdown",
    "run_main",
]


if __name__ == "__main__":
    run_main()
